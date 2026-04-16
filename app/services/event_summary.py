import re

from ollama import Client

from app.config import settings

MAX_SUMMARY_WORDS = 30
TRAILING_FILLER_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "via",
    "with",
}


def build_event_summary_client() -> Client:
    return Client(
        host=settings.ollama_base_url,
        timeout=float(settings.ollama_timeout_seconds),
    )


def _extract_message_content(response) -> str:
    if hasattr(response, "message") and hasattr(response.message, "content"):
        return response.message.content or ""

    if isinstance(response, dict):
        message = response.get("message", {})
        if isinstance(message, dict):
            return message.get("content", "") or ""

    return ""


def normalize_summary_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip().strip("\"'")
    words = cleaned.split()
    trimmed_words = words[:MAX_SUMMARY_WORDS]
    while trimmed_words and trimmed_words[-1].lower().rstrip(".,;:!?") in TRAILING_FILLER_WORDS:
        trimmed_words.pop()
    return " ".join(trimmed_words)


def summarize_event_payload(payload: str) -> str:
    client = build_event_summary_client()
    response = client.chat(
        model=settings.ollama_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You summarize application event payloads. "
                    "Reply with a single plain-text summary of at most 30 words. "
                    "Use only facts explicitly present in the payload. "
                    "Preserve identifiers exactly and do not invent or infer details. "
                    "Do not use bullets, quotes, headings, JSON, or prefixes."
                ),
            },
            {
                "role": "user",
                "content": f"Summarize this event payload:\n{payload}",
            },
        ],
        options={"temperature": 0},
    )
    summary = normalize_summary_text(_extract_message_content(response))
    if not summary:
        raise ValueError("Ollama returned an empty summary.")
    return summary

from app.config import settings
from app.services.ollama_client import build_ollama_client


class PhraseGenerator:

    def generate(self) -> str:
        client = build_ollama_client()
        response = client.chat(
            model=settings.ollama_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You generate random paragraphs on arbitrary topics. "
                        "Reply with exactly one plain-text paragraph between 50 and 70 words. "
                        "Do not use bullets, headings, quotes, or any formatting."
                    ),
                },
                {
                    "role": "user",
                    "content": "Write a random paragraph.",
                },
            ],
            options={"temperature": 0.7},
        )
        if hasattr(response, "message") and hasattr(response.message, "content"):
            return (response.message.content or "").strip()
        if isinstance(response, dict):
            message = response.get("message", {})
            if isinstance(message, dict):
                return (message.get("content", "") or "").strip()
        return ""

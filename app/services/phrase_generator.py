from app.config import settings
from app.services.ollama_client import build_ollama_client


class PhraseGenerator:

    def generate(self, source_name: str | None = None, hint: str | None = None) -> str:
        client = build_ollama_client()

        if source_name and hint:
            system_content = (
                f"You generate realistic event payloads for {source_name}. "
                "Reply with exactly one plain-text paragraph between 50 and 70 words. "
                "Do not use bullets, headings, quotes, or any formatting."
            )
            user_content = f"Write a {source_name} event payload about: {hint}"
        else:
            system_content = (
                "You generate random paragraphs on arbitrary sales topics. "
                "Reply with exactly one plain-text paragraph between 50 and 70 words. "
                "Do not use bullets, headings, quotes, or any formatting."
            )
            user_content = "Write a random paragraph."

        response = client.chat(
            model=settings.ollama_model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
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

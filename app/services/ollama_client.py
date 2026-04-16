from ollama import Client

from app.config import settings


def build_ollama_client() -> Client:
    return Client(
        host=settings.ollama_base_url,
        timeout=float(settings.ollama_timeout_seconds),
    )

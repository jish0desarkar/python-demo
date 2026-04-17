from dataclasses import dataclass

from app.config import settings
from app.services.ollama_client import build_ollama_client


@dataclass(frozen=True)
class EmbeddingModelInfo:
    name: str
    dim: int


AVAILABLE_EMBEDDING_MODELS: dict[str, EmbeddingModelInfo] = {
    "nomic-embed-text": EmbeddingModelInfo("nomic-embed-text", 768),
    "mxbai-embed-large": EmbeddingModelInfo("mxbai-embed-large", 1024),
}


class Embedder:
    def __init__(self, info: EmbeddingModelInfo):
        self.info = info
        self._client = build_ollama_client()

    @property
    def model_key(self) -> str:
        return self.info.name

    @property
    def dim(self) -> int:
        return self.info.dim

    def embed(self, text: str) -> list[float]:
        response = self._client.embed(model=self.info.name, input=text)
        return response["embeddings"][0]


class LLMService:
    @staticmethod
    def active_embedder() -> Embedder:
        name = settings.embedding_model
        if name not in AVAILABLE_EMBEDDING_MODELS:
            raise ValueError(
                f"Unsupported embedding model '{name}'. "
                f"Available: {list(AVAILABLE_EMBEDDING_MODELS)}"
            )
        return Embedder(AVAILABLE_EMBEDDING_MODELS[name])

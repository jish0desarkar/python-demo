import os

import faiss
import numpy as np
from ollama import Client

from app.config import settings

FAISS_INDEX_PATH = "/app/data/faiss_event_summaries_index.faiss"
EMBEDDING_MODEL = "nomic-embed-text"


class EmbeddingStore:

    def get_embedding(self, text: str) -> list[float]:
        client = Client(host=settings.ollama_base_url)
        response = client.embed(model=EMBEDDING_MODEL, input=text)
        return response["embeddings"][0]

    def load_index(self):
        if os.path.exists(FAISS_INDEX_PATH):
            return faiss.read_index(FAISS_INDEX_PATH)
        return None

    def store(self, summary_id: int, text: str):
        embedding = self.get_embedding(text)
        vector = np.array([embedding], dtype=np.float32)
        ids = np.array([summary_id], dtype=np.int64)

        index = self.load_index()
        if index is None:
            dim = vector.shape[1]
            index = faiss.IndexIDMap(faiss.IndexFlatL2(dim))

        index.add_with_ids(vector, ids)
        faiss.write_index(index, FAISS_INDEX_PATH)

    def search(self, query: str, k: int = 3) -> list[int]:
        index = self.load_index()
        if index is None:
            return []

        embedding = self.get_embedding(query)
        vector = np.array([embedding], dtype=np.float32)
        distances, ids = index.search(vector, k)
        return [int(i) for i in ids[0] if i != -1]

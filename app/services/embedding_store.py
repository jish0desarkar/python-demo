import os

import faiss
import numpy as np
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models import EventSummaryEmbedding
from app.services.llm import Embedder, LLMService

FAISS_DIR = "/app/data/faiss"


class EmbeddingStore:

    def __init__(self, embedder: Embedder | None = None):
        self._embedder = embedder or LLMService.active_embedder()

    def _index_path(self) -> str:
        return f"{FAISS_DIR}/{self._embedder.model_key}.faiss"

    def load_index(self):
        path = self._index_path()
        if not os.path.exists(path):
            return None
        index = faiss.read_index(path)
        
        return index

    def _new_index(self):
        return faiss.IndexIDMap(faiss.IndexFlatL2(self._embedder.dim))

    def _write_index(self, index) -> None:
        os.makedirs(FAISS_DIR, exist_ok=True)
        faiss.write_index(index, self._index_path())

    def store(self, db: Session, summary_id: int, text: str) -> None:
        self.store_many(db, [(summary_id, text)])

    def store_many(self, db: Session, rows: list[tuple[int, str]]) -> None:
        if not rows:
            return

        vectors = np.array(
            [self._embedder.embed(text) for _, text in rows],
            dtype=np.float32,
        )
        ids = np.array([summary_id for summary_id, _ in rows], dtype=np.int64)

        index = self.load_index() or self._new_index()
        index.add_with_ids(vectors, ids)
        self._write_index(index)

        stmt = sqlite_insert(EventSummaryEmbedding).values([
            {"model_key": self._embedder.model_key, "event_summary_id": summary_id}
            for summary_id, _ in rows
        ]).on_conflict_do_nothing()
        db.execute(stmt)
        db.commit()

    def search(self, query: str, k: int = 10) -> list[int]:
        index = self.load_index()
        if index is None:
            return []

        embedding = self._embedder.embed(query)
        vector = np.array([embedding], dtype=np.float32)
        _distances, ids = index.search(vector, k)
        return [int(i) for i in ids[0] if i != -1]

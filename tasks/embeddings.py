import os

import faiss
import numpy as np
from ollama import Client

from app.config import settings
from app.database import SessionLocal
from app.models import EventSummary
from celery_app import celery_app

FAISS_INDEX_PATH = "/app/data/faiss_event_summaries_index.faiss"
EMBEDDING_MODEL = "nomic-embed-text"


def get_embedding(text: str) -> list[float]:
    client = Client(host=settings.ollama_base_url)
    response = client.embed(model=EMBEDDING_MODEL, input=text)
    return response["embeddings"][0]


@celery_app.task(name="tasks.embeddings.store_event_summary_embedding")
def store_event_summary_embedding(event_summary_id: int) -> dict[str, str | int]:
    db = SessionLocal()
    try:
        summary = db.get(EventSummary, event_summary_id)
        if summary is None:
            return {"status": "missing", "event_summary_id": event_summary_id}

        embedding = get_embedding(summary.summary)
        vector = np.array([embedding], dtype=np.float32)
        ids = np.array([summary.id], dtype=np.int64)

        if os.path.exists(FAISS_INDEX_PATH):
            index = faiss.read_index(FAISS_INDEX_PATH)
        else:
            dim = vector.shape[1]
            base_index = faiss.IndexFlatL2(dim)
            index = faiss.IndexIDMap(base_index)

        index.add_with_ids(vector, ids)
        faiss.write_index(index, FAISS_INDEX_PATH)

        return {"status": "stored", "event_summary_id": event_summary_id}
    finally:
        db.close()

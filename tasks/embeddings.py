from app.database import SessionLocal
from app.models import EventSummary
from app.services.embedding_store import EmbeddingStore
from celery_app import celery_app


@celery_app.task(name="tasks.embeddings.store_event_summary_embedding")
def store_event_summary_embedding(event_summary_id: int) -> dict[str, str | int]:
    db = SessionLocal()
    try:
        summary = db.get(EventSummary, event_summary_id)
        if summary is None:
            return {"status": "missing", "event_summary_id": event_summary_id}

        EmbeddingStore().store(summary.id, summary.summary)
        return {"status": "stored", "event_summary_id": event_summary_id}
    finally:
        db.close()

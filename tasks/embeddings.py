from sqlalchemy import select

from app.database import SessionLocal
from app.models import EventSummary, EventSummaryEmbedding
from app.services.embedding_store import EmbeddingStore
from app.services.llm import LLMService
from celery_app import celery_app

BACKFILL_BATCH_SIZE = 50


@celery_app.task(name="tasks.embeddings.store_event_summary_embedding")
def store_event_summary_embedding(event_summary_id: int) -> dict[str, str | int]:
    db = SessionLocal()
    try:
        summary = db.get(EventSummary, event_summary_id)
        if summary is None:
            return {"status": "missing", "event_summary_id": event_summary_id}

        EmbeddingStore().store(db, summary.id, summary.summary)
        return {"status": "stored", "event_summary_id": event_summary_id}
    finally:
        db.close()


@celery_app.task(name="tasks.embeddings.backfill_active_model_embeddings")
def backfill_active_model_embeddings(
    batch_size: int = BACKFILL_BATCH_SIZE,
) -> dict[str, str | int]:
    embedder = LLMService.active_embedder()
    db = SessionLocal()
    try:
        missing = db.execute(
            select(EventSummary.id, EventSummary.summary)
            .outerjoin(
                EventSummaryEmbedding,
                (EventSummaryEmbedding.event_summary_id == EventSummary.id)
                & (EventSummaryEmbedding.model_key == embedder.model_key),
            )
            .where(EventSummaryEmbedding.event_summary_id.is_(None))
            .order_by(EventSummary.id)
            .limit(batch_size)
        ).all()

        if not missing:
            return {"status": "idle", "model_key": embedder.model_key, "processed": 0}

        rows = [(summary_id, text) for summary_id, text in missing]
        EmbeddingStore(embedder).store_many(db, rows)
    finally:
        db.close()

    backfill_active_model_embeddings.delay(batch_size)
    return {
        "status": "processed",
        "model_key": embedder.model_key,
        "processed": len(rows),
    }

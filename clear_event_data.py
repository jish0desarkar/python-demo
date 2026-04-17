"""Remove all events and related rows (queued requests, summaries, filter logs, event logs).

Run (e.g. in the web container):
    docker compose run --rm --no-deps web python clear_event_data.py
"""

import shutil

from sqlalchemy import delete, func, select

from app.database import SessionLocal
from app.models import Event, QueuedEventRequest
from app.services.embedding_store import FAISS_DIR


def main() -> None:
    with SessionLocal() as db:
        n_qer = db.execute(select(func.count()).select_from(QueuedEventRequest)).scalar_one()
        n_ev = db.execute(select(func.count()).select_from(Event)).scalar_one()
        db.execute(delete(QueuedEventRequest))
        db.execute(delete(Event))
        db.commit()
        print(
            f"Cleared {n_qer} queued_event_requests and {n_ev} events "
            "(event_summary, event_summary_embeddings, event_filter_logs, event_logs removed via CASCADE)."
        )

    shutil.rmtree(FAISS_DIR, ignore_errors=True)
    print(f"Removed FAISS index directory: {FAISS_DIR}")


if __name__ == "__main__":
    main()

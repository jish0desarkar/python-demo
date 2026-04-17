"""Remove all events and related rows (queued requests, summaries, filter logs, event logs).

Run (e.g. in the web container):
    docker exec python-demo-web python clear_event_data.py
"""

from sqlalchemy import delete, func, select

from app.database import SessionLocal
from app.models import Event, QueuedEventRequest


def main() -> None:
    with SessionLocal() as db:
        n_qer = db.execute(select(func.count()).select_from(QueuedEventRequest)).scalar_one()
        n_ev = db.execute(select(func.count()).select_from(Event)).scalar_one()
        db.execute(delete(QueuedEventRequest))
        db.execute(delete(Event))
        db.commit()
        print(
            f"Cleared {n_qer} queued_event_requests and {n_ev} events "
            "(event_summary, event_filter_logs, event_logs removed via CASCADE)."
        )


if __name__ == "__main__":
    main()

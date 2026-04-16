from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Account,
    Event,
    EventFilterLog,
    EventSummary,
    QueuedEventRequest,
    Rule,
    Source,
    account_sources,
)
from app.services.event_filter import EventFilter
from app.services.event_summary import summarize_event_payload
from celery_app import celery_app
from tasks.embeddings import store_event_summary_embedding

SUMMARY_RETRY_ATTEMPTS = 3


def is_source_linked_to_account(db, account_id: int, source_id: int) -> bool:
    linked_source_id = db.scalar(
        select(account_sources.c.source_id).where(
            account_sources.c.account_id == account_id,
            account_sources.c.source_id == source_id,
        )
    )
    return linked_source_id is not None


def mark_request_failed(
    db, queued_event_request: QueuedEventRequest, message: str
) -> dict[str, str]:
    queued_event_request.status = "failed"
    queued_event_request.error_message = message[:255]
    db.commit()
    return {"status": "failed", "error": queued_event_request.error_message}


def create_event_record(db, queued_event_request: QueuedEventRequest) -> Event:
    event = Event(
        account_id=queued_event_request.account_id,
        source_id=queued_event_request.source_id,
        payload=queued_event_request.payload,
    )
    db.add(event)
    db.flush()
    queued_event_request.event_id = event.id
    db.commit()
    db.refresh(event)
    return event


def get_event_record(db, queued_event_request: QueuedEventRequest) -> Event | None:
    if queued_event_request.event_id is None:
        return None
    return db.get(Event, queued_event_request.event_id)


def create_summary_record(db, event: Event) -> bool:
    existing_summary = db.scalar(
        select(EventSummary).where(EventSummary.event_id == event.id)
    )
    if existing_summary is not None:
        return True

    for _ in range(SUMMARY_RETRY_ATTEMPTS):
        try:
            summary_record = EventSummary(
                account_id=event.account_id,
                event_id=event.id,
                summary=summarize_event_payload(event.payload),
            )
            db.add(summary_record)
            db.commit()
            return True
        except Exception:
            db.rollback()

    return False


@celery_app.task(name="tasks.events.process_queued_event_request")
def process_queued_event_request(queued_event_request_id: int) -> dict[str, int | str]:
    db = SessionLocal()
    try:
        queued_event_request = db.get(QueuedEventRequest, queued_event_request_id)
        if queued_event_request is None:
            return {"status": "missing", "queued_event_request_id": queued_event_request_id}
        if queued_event_request.status == "completed" and queued_event_request.event_id is not None:
            return {
                "status": "completed",
                "queued_event_request_id": queued_event_request.id,
                "event_id": queued_event_request.event_id,
            }

        queued_event_request.status = "processing"
        queued_event_request.error_message = None
        db.commit()

        account = db.get(Account, queued_event_request.account_id)
        if account is None:
            return mark_request_failed(db, queued_event_request, "Account not found.")

        source = db.get(Source, queued_event_request.source_id)
        if source is None or not is_source_linked_to_account(
            db,
            queued_event_request.account_id,
            queued_event_request.source_id,
        ):
            return mark_request_failed(
                db,
                queued_event_request,
                "Source not found for account.",
            )

        try:
            event = get_event_record(db, queued_event_request)
            if event is None:
                event = create_event_record(db, queued_event_request)

            summary_created = create_summary_record(
                db,
                event
            )

            if summary_created:
                event_summary = db.scalar(
                    select(EventSummary).where(EventSummary.event_id == event.id)
                )
                if event_summary:
                    store_event_summary_embedding.delay(event_summary.id)

            queued_event_request.status = "completed"
            queued_event_request.error_message = None
            db.commit()
            return {
                "status": "completed",
                "queued_event_request_id": queued_event_request.id,
                "event_id": event.id,
                "summary_created": str(summary_created),
            }
        except Exception as exc:
            db.rollback()
            queued_event_request = db.get(QueuedEventRequest, queued_event_request_id)
            if queued_event_request is None:
                raise

            queued_event_request.status = "failed"
            queued_event_request.error_message = str(exc)[:255]
            db.commit()
            raise
    finally:
        db.close()


@celery_app.task(name="tasks.events.filter_unprocessed_events")
def filter_unprocessed_events() -> dict[str, int]:
    db = SessionLocal()
    processed = 0
    try:
        unfiltered_events = db.scalars(
            select(Event).where(Event.is_filtered == False) 
        ).all()

        for event in unfiltered_events:
            rules = db.scalars(
                select(Rule).where(Rule.source_id == event.source_id)
            ).all()

            if not rules:
                continue

            matched_rule, score = EventFilter().match(rules, event.payload)

            if matched_rule is not None:
                log = EventFilterLog(
                    rule_id=matched_rule.id,
                    event_id=event.id,
                    status="passed",
                    score=score,
                )
            else:
                log = EventFilterLog(
                    rule_id=None,
                    event_id=event.id,
                    status="failed",
                    score=score,
                )

            db.add(log)
            event.is_filtered = True
            db.commit()
            processed += 1

        return {"processed": processed}
    finally:
        db.close()

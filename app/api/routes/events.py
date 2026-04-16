from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import EventCreate
from app.database import get_db
from app.models import Account, Event, EventFilterLog, EventSummary, QueuedEventRequest, Source, account_sources
from app.services.embedding_store import EmbeddingStore
from celery_app import celery_app

router = APIRouter(prefix="/events", tags=["events"])
templates = Jinja2Templates(directory="app/templates")
IN_PROCESS_EVENT_STATUSES = ("queued", "processing")


def get_event(db: Session, event_id: int) -> Event:
    event = db.scalar(
        select(Event)
        .options(
            selectinload(Event.account),
            selectinload(Event.source).selectinload(Source.rules),
            selectinload(Event.summary_record),
            selectinload(Event.filter_logs).selectinload(EventFilterLog.rule),
        )
        .where(Event.id == event_id)
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def list_accounts_data(db: Session) -> list[Account]:
    return db.scalars(select(Account).order_by(Account.id)).all()


def list_sources_data(db: Session) -> list[Source]:
    return db.scalars(select(Source).order_by(Source.id)).all()


def list_events_data(
    db: Session,
    source_id: int | None = None,
    event_ids: list[int] | None = None,
) -> list[Event]:
    query = (
        select(Event)
        .options(
            selectinload(Event.account),
            selectinload(Event.source),
            selectinload(Event.summary_record),
            selectinload(Event.filter_logs).selectinload(EventFilterLog.rule),
        )
        .order_by(Event.id)
    )
    if event_ids is not None:
        query = query.where(Event.id.in_(event_ids))
    if source_id is not None:
        query = query.where(Event.source_id == source_id)

    return db.scalars(query).all()


def count_in_process_event_requests(db: Session) -> int:
    return db.scalar(
        select(func.count()).select_from(QueuedEventRequest).where(
            QueuedEventRequest.status.in_(IN_PROCESS_EVENT_STATUSES)
        )
    ) or 0


def get_event_sources(db: Session, account_id: int | None) -> list[Source]:
    if account_id is None:
        return []
    return db.scalars(
        select(Source)
        .join(account_sources, account_sources.c.source_id == Source.id)
        .where(account_sources.c.account_id == account_id)
        .order_by(Source.id)
    ).all()


def is_source_linked_to_account(db: Session, account_id: int, source_id: int) -> bool:
    linked_source_id = db.scalar(
        select(account_sources.c.source_id).where(
            account_sources.c.account_id == account_id,
            account_sources.c.source_id == source_id,
        )
    )
    return linked_source_id is not None


def event_panel_context(
    db: Session,
    *,
    account_id: int | None = None,
    source_id: int | None = None,
    filter_source_id: int | None = None,
    search_query: str = "",
    payload_text: str = "",
    error: str | None = None,
    message: str | None = None,
) -> dict:
    accounts = list_accounts_data(db)
    selected_account_id = account_id
    if selected_account_id is None and accounts:
        selected_account_id = accounts[0].id

    event_ids = None
    if search_query:
        summary_ids = EmbeddingStore().search(search_query)
        if summary_ids:
            event_ids = [
                row[0]
                for row in db.execute(
                    select(EventSummary.event_id).where(
                        EventSummary.id.in_(summary_ids)
                    )
                ).all()
            ]
        else:
            event_ids = []

    return {
        "events": list_events_data(db, source_id=filter_source_id, event_ids=event_ids),
        "accounts": accounts,
        "sources": get_event_sources(db, selected_account_id),
        "event_filter_sources": list_sources_data(db),
        "event_filters": {
            "source_id": filter_source_id,
            "search_query": search_query,
        },
        "form_data": {
            "account_id": selected_account_id,
            "source_id": source_id,
            "payload_text": payload_text,
        },
        "processing_event_count": count_in_process_event_requests(db),
        "error": error,
        "message": message,
    }


def render_events(
    request: Request,
    db: Session,
    *,
    account_id: int | None = None,
    source_id: int | None = None,
    filter_source_id: int | None = None,
    search_query: str = "",
    payload_text: str = "",
    error: str | None = None,
    message: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/partials/event/events_panel.html",
        {
            "request": request,
            **event_panel_context(
                db,
                account_id=account_id,
                source_id=source_id,
                filter_source_id=filter_source_id,
                search_query=search_query,
                payload_text=payload_text,
                error=error,
                message=message,
            ),
        },
        status_code=status_code,
    )


def render_events_list(
    request: Request,
    db: Session,
    *,
    filter_source_id: int | None = None,
    search_query: str = "",
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/partials/event/events_list.html",
        {
            "request": request,
            **event_panel_context(
                db,
                filter_source_id=filter_source_id,
                search_query=search_query,
            ),
        },
        status_code=status_code,
    )


def render_event_detail(
    request: Request,
    db: Session,
    event_id: int,
    *,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/partials/event/event_detail.html",
        {"request": request, "event": get_event(db, event_id)},
        status_code=status_code,
    )


@router.get("", response_class=HTMLResponse)
def list_events(
    request: Request,
    account_id: str = "",
    source_id: str = "",
    filter_source_id: str = "",
    search_query: str = "",
    payload: str = "",
    db: Session = Depends(get_db),
):
    parsed_account_id = None
    if account_id.strip():
        try:
            parsed_account_id = int(account_id)
        except ValueError:
            parsed_account_id = None

    parsed_source_id = None
    if source_id.strip():
        try:
            parsed_source_id = int(source_id)
        except ValueError:
            parsed_source_id = None

    parsed_filter_source_id = None
    if filter_source_id.strip():
        try:
            parsed_filter_source_id = int(filter_source_id)
        except ValueError:
            parsed_filter_source_id = None

    return render_events(
        request,
        db,
        account_id=parsed_account_id,
        source_id=parsed_source_id,
        filter_source_id=parsed_filter_source_id,
        search_query=search_query.strip(),
        payload_text=payload,
    )


@router.get("/list", response_class=HTMLResponse)
def list_events_partial(
    request: Request,
    filter_source_id: str = "",
    search_query: str = "",
    db: Session = Depends(get_db),
):
    parsed_filter_source_id = None
    if filter_source_id.strip():
        try:
            parsed_filter_source_id = int(filter_source_id)
        except ValueError:
            parsed_filter_source_id = None

    return render_events_list(
        request,
        db,
        filter_source_id=parsed_filter_source_id,
        search_query=search_query.strip(),
    )


@router.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
def create_event_webhook(
    event_data: EventCreate,
    db: Session = Depends(get_db),
):
    account = db.get(Account, event_data.account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found.")

    source = db.get(Source, event_data.source_id)
    if source is None or not is_source_linked_to_account(
        db, event_data.account_id, event_data.source_id
    ):
        raise HTTPException(status_code=404, detail="Source not found for account.")

    queued_event_request = QueuedEventRequest(
        account_id=event_data.account_id,
        source_id=event_data.source_id,
        payload=event_data.payload,
        status="queued",
    )
    db.add(queued_event_request)
    db.commit()
    db.refresh(queued_event_request)

    try:
        celery_app.send_task(
            "tasks.events.process_queued_event_request",
            args=[queued_event_request.id],
        )
    except Exception:
        queued_event_request.status = "failed"
        queued_event_request.error_message = "Unable to queue event processing."
        db.commit()
        raise HTTPException(
            status_code=503, detail="Unable to queue event processing."
        )

    return {
        "status": "queued",
        "queued_event_request_id": queued_event_request.id,
    }


@router.post("", response_class=HTMLResponse)
def create_event(
    request: Request,
    account_id: str = Form(""),
    source_id: str = Form(""),
    payload: str = Form(""),
    db: Session = Depends(get_db),
):
    account_value = account_id.strip()
    if not account_value:
        return render_events(
            request,
            db,
            payload_text=payload,
            error="Account is required.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    try:
        parsed_account_id = int(account_value)
    except ValueError:
        return render_events(
            request,
            db,
            payload_text=payload,
            error="Account must be a number.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    source_value = source_id.strip()
    if not source_value:
        return render_events(
            request,
            db,
            account_id=parsed_account_id,
            payload_text=payload,
            error="Source is required.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    try:
        parsed_source_id = int(source_value)
    except ValueError:
        return render_events(
            request,
            db,
            account_id=parsed_account_id,
            payload_text=payload,
            error="Source must be a number.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        validated = EventCreate(
            account_id=parsed_account_id,
            source_id=parsed_source_id,
            payload=payload,
        )
    except ValidationError as exc:
        return render_events(
            request,
            db,
            account_id=parsed_account_id,
            source_id=parsed_source_id,
            payload_text=payload,
            error=exc.errors()[0]["msg"],
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    account = db.get(Account, validated.account_id)
    if account is None:
        return render_events(
            request,
            db,
            account_id=parsed_account_id,
            source_id=parsed_source_id,
            payload_text=payload,
            error="Account not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    source = db.get(Source, validated.source_id)
    if source is None or not is_source_linked_to_account(
        db, validated.account_id, validated.source_id
    ):
        return render_events(
            request,
            db,
            account_id=parsed_account_id,
            source_id=parsed_source_id,
            payload_text=payload,
            error="Source not found for account.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    queued_event_request = QueuedEventRequest(
        account_id=validated.account_id,
        source_id=validated.source_id,
        payload=validated.payload,
        status="queued",
    )
    db.add(queued_event_request)
    db.commit()
    db.refresh(queued_event_request)

    try:
        celery_app.send_task(
            "tasks.events.process_queued_event_request",
            args=[queued_event_request.id],
        )
    except Exception:
        queued_event_request.status = "failed"
        queued_event_request.error_message = "Unable to queue event processing."
        db.commit()
        return render_events(
            request,
            db,
            account_id=validated.account_id,
            source_id=validated.source_id,
            payload_text=payload,
            error="Unable to queue event processing.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return render_events(
        request,
        db,
        account_id=validated.account_id,
        message="Event is being processed, please wait.",
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get("/{event_id}", response_class=HTMLResponse)
def show_event(request: Request, event_id: int, db: Session = Depends(get_db)):
    return render_event_detail(request, db, event_id)

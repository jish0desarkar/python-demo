from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import AccountCreate, SourceLinkCreate
from app.database import get_db
from app.models import Account, Source, account_sources

router = APIRouter(prefix="/accounts", tags=["accounts"])
templates = Jinja2Templates(directory="app/templates")


def get_account(db: Session, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


def list_accounts_data(db: Session) -> list[Account]:
    return db.scalars(select(Account).order_by(Account.id)).all()


def list_account_sources_data(db: Session, account_id: int) -> list[Source]:
    return db.scalars(
        select(Source)
        .join(account_sources, account_sources.c.source_id == Source.id)
        .where(account_sources.c.account_id == account_id)
        .order_by(Source.id)
    ).all()


def list_available_sources_data(db: Session, account_id: int) -> list[Source]:
    linked_source_ids = select(account_sources.c.source_id).where(
        account_sources.c.account_id == account_id
    )
    return db.scalars(
        select(Source).where(~Source.id.in_(linked_source_ids)).order_by(Source.id)
    ).all()


def is_source_linked_to_account(db: Session, account_id: int, source_id: int) -> bool:
    linked_source_id = db.scalar(
        select(account_sources.c.source_id).where(
            account_sources.c.account_id == account_id,
            account_sources.c.source_id == source_id,
        )
    )
    return linked_source_id is not None


def account_panel_context(
    db: Session,
    *,
    name: str = "",
    error: str | None = None,
    message: str | None = None,
) -> dict:
    return {
        "accounts": list_accounts_data(db),
        "form_data": {"name": name},
        "error": error,
        "message": message,
    }


def source_panel_context(
    db: Session,
    account_id: int,
    *,
    source_id: int | None = None,
    error: str | None = None,
    message: str | None = None,
) -> dict:
    return {
        "account": get_account(db, account_id),
        "sources": list_account_sources_data(db, account_id),
        "available_sources": list_available_sources_data(db, account_id),
        "form_data": {"source_id": source_id},
        "error": error,
        "message": message,
    }


def render_accounts(
    request: Request,
    db: Session,
    *,
    name: str = "",
    error: str | None = None,
    message: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/partials/account/accounts_panel.html",
        {
            "request": request,
            **account_panel_context(db, name=name, error=error, message=message),
        },
        status_code=status_code,
    )


def render_account_detail(
    request: Request,
    db: Session,
    account_id: int,
    *,
    source_id: int | None = None,
    error: str | None = None,
    message: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/partials/account/account_detail.html",
        {
            "request": request,
            **source_panel_context(
                db,
                account_id,
                source_id=source_id,
                error=error,
                message=message,
            ),
        },
        status_code=status_code,
    )


@router.get("", response_class=HTMLResponse)
def list_accounts(request: Request, db: Session = Depends(get_db)):
    return render_accounts(request, db)


@router.post("", response_class=HTMLResponse)
def create_account(
    request: Request,
    name: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        payload = AccountCreate(name=name.strip())
    except ValidationError as exc:
        return render_accounts(
            request,
            db,
            name=name,
            error=exc.errors()[0]["msg"],
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    account = Account(name=payload.name)
    db.add(account)
    db.commit()

    return render_accounts(
        request,
        db,
        message=f"Created account {account.name}.",
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/{account_id}", response_class=HTMLResponse)
def show_account(request: Request, account_id: int, db: Session = Depends(get_db)):
    return render_account_detail(request, db, account_id)


@router.post(
    "/{account_id}/sources",
    response_class=HTMLResponse,
)
def create_account_source(
    request: Request,
    account_id: int,
    source_id: str = Form(""),
    db: Session = Depends(get_db),
):
    account = get_account(db, account_id)
    source_value = source_id.strip()
    if not source_value:
        return render_account_detail(
            request,
            db,
            account_id,
            error="Source is required.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    try:
        parsed_source_id = int(source_value)
    except ValueError:
        return render_account_detail(
            request,
            db,
            account_id,
            error="Source must be a number.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        payload = SourceLinkCreate(source_id=parsed_source_id)
    except ValidationError as exc:
        return render_account_detail(
            request,
            db,
            account_id,
            source_id=parsed_source_id,
            error=exc.errors()[0]["msg"],
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    source = db.get(Source, payload.source_id)
    if source is None:
        return render_account_detail(
            request,
            db,
            account_id,
            source_id=parsed_source_id,
            error="Source not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if is_source_linked_to_account(db, account_id, payload.source_id):
        return render_account_detail(
            request,
            db,
            account_id,
            source_id=parsed_source_id,
            error="Source already linked to this account.",
            status_code=status.HTTP_409_CONFLICT,
        )

    account.sources.append(source)
    db.commit()

    return render_account_detail(
        request,
        db,
        account_id,
        message=f"Added source {source.name}.",
        status_code=status.HTTP_201_CREATED,
    )


@router.delete(
    "/{account_id}/sources/{source_id}",
    response_class=HTMLResponse,
)
def delete_account_source(
    request: Request,
    account_id: int,
    source_id: int,
    db: Session = Depends(get_db),
):
    account = get_account(db, account_id)

    source = db.get(Source, source_id)
    if source is None or not is_source_linked_to_account(db, account_id, source_id):
        return render_account_detail(
            request,
            db,
            account_id,
            error="Source not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    account.sources.remove(source)
    db.commit()

    return render_account_detail(
        request,
        db,
        account_id,
        message=f"Removed source {source.name} from {account.name}.",
    )

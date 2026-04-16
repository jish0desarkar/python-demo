from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import SourceCreate
from app.database import get_db
from app.models import Source

router = APIRouter(prefix="/sources", tags=["sources"])
templates = Jinja2Templates(directory="app/templates")


def get_source(db: Session, source_id: int) -> Source:
    source = db.scalar(
        select(Source).options(selectinload(Source.accounts)).where(Source.id == source_id)
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


def list_sources_data(db: Session) -> list[Source]:
    return db.scalars(
        select(Source).options(selectinload(Source.accounts)).order_by(Source.id)
    ).all()


def source_catalog_context(
    db: Session,
    *,
    key: str = "",
    name: str = "",
    error: str | None = None,
    message: str | None = None,
) -> dict:
    return {
        "sources": list_sources_data(db),
        "form_data": {"key": key, "name": name},
        "error": error,
        "message": message,
    }


def render_sources(
    request: Request,
    db: Session,
    *,
    key: str = "",
    name: str = "",
    error: str | None = None,
    message: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/partials/source/source_catalog_panel.html",
        {
            "request": request,
            **source_catalog_context(
                db,
                key=key,
                name=name,
                error=error,
                message=message,
            ),
        },
        status_code=status_code,
    )


@router.get("", response_class=HTMLResponse)
def list_sources(request: Request, db: Session = Depends(get_db)):
    return render_sources(request, db)


@router.post("", response_class=HTMLResponse)
def create_source(
    request: Request,
    key: str = Form(""),
    name: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        payload = SourceCreate(key=key.strip(), name=name.strip())
    except ValidationError as exc:
        return render_sources(
            request,
            db,
            key=key,
            name=name,
            error=exc.errors()[0]["msg"],
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    source = Source(key=payload.key, name=payload.name)
    db.add(source)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render_sources(
            request,
            db,
            key=key,
            name=name,
            error="Source key already exists.",
            status_code=status.HTTP_409_CONFLICT,
        )

    return render_sources(
        request,
        db,
        message=f"Created source {source.name}.",
        status_code=status.HTTP_201_CREATED,
    )


@router.delete("/{source_id}", response_class=HTMLResponse)
def delete_source(request: Request, source_id: int, db: Session = Depends(get_db)):
    source = get_source(db, source_id)

    if source.accounts:
        return render_sources(
            request,
            db,
            error=f"Cannot delete {source.name} while it is linked to accounts.",
            status_code=status.HTTP_409_CONFLICT,
        )

    db.delete(source)
    db.commit()

    return render_sources(request, db, message=f"Deleted source {source.name}.")

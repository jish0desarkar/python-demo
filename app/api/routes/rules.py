from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Rule

router = APIRouter(prefix="/rules", tags=["rules"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def list_rules(request: Request, db: Session = Depends(get_db)):
    rules = db.scalars(
        select(Rule).options(selectinload(Rule.source)).order_by(Rule.source_id, Rule.id)
    ).all()
    return templates.TemplateResponse(
        "ui/partials/rules_panel.html",
        {"request": request, "rules": rules},
    )

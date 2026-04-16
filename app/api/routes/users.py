from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import UserCreate
from app.database import get_db
from app.models import Account, User

router = APIRouter(prefix="/users", tags=["users"])
templates = Jinja2Templates(directory="app/templates")


def get_user(db: Session, user_id: int) -> User:
    user = db.scalar(
        select(User).options(selectinload(User.account)).where(User.id == user_id)
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def list_accounts_data(db: Session) -> list[Account]:
    return db.scalars(select(Account).order_by(Account.id)).all()


def list_users_data(db: Session) -> list[User]:
    return db.scalars(
        select(User).options(selectinload(User.account)).order_by(User.id)
    ).all()


def user_panel_context(
    db: Session,
    *,
    name: str = "",
    email: str = "",
    account_id: int | None = None,
    error: str | None = None,
    message: str | None = None,
) -> dict:
    return {
        "users": list_users_data(db),
        "accounts": list_accounts_data(db),
        "form_data": {
            "name": name,
            "email": email,
            "account_id": account_id,
        },
        "error": error,
        "message": message,
    }


def render_users(
    request: Request,
    db: Session,
    *,
    name: str = "",
    email: str = "",
    account_id: int | None = None,
    error: str | None = None,
    message: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/partials/user/users_panel.html",
        {
            "request": request,
            **user_panel_context(
                db,
                name=name,
                email=email,
                account_id=account_id,
                error=error,
                message=message,
            ),
        },
        status_code=status_code,
    )


def render_user_detail(
    request: Request,
    db: Session,
    user_id: int,
    *,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/partials/user/user_detail.html",
        {"request": request, "user": get_user(db, user_id)},
        status_code=status_code,
    )


@router.get("", response_class=HTMLResponse)
def list_users(request: Request, db: Session = Depends(get_db)):
    return render_users(request, db)


@router.post("", response_class=HTMLResponse)
def create_user(
    request: Request,
    name: str = Form(""),
    email: str = Form(""),
    account_id: str = Form(""),
    db: Session = Depends(get_db),
):
    account_value = account_id.strip()
    if not account_value:
        return render_users(
            request,
            db,
            name=name,
            email=email,
            error="Account is required.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    try:
        parsed_account_id = int(account_value)
    except ValueError:
        return render_users(
            request,
            db,
            name=name,
            email=email,
            error="Account must be a number.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        payload = UserCreate(
            name=name.strip(),
            email=email.strip(),
            account_id=parsed_account_id,
        )
    except ValidationError as exc:
        return render_users(
            request,
            db,
            name=name,
            email=email,
            account_id=parsed_account_id,
            error=exc.errors()[0]["msg"],
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    account = db.get(Account, payload.account_id)
    if account is None:
        return render_users(
            request,
            db,
            name=name,
            email=email,
            account_id=parsed_account_id,
            error="Account not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    user = User(name=payload.name, email=payload.email, account_id=payload.account_id)
    db.add(user)
    db.commit()

    return render_users(
        request,
        db,
        message=f"Created user {user.name}.",
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/{user_id}", response_class=HTMLResponse)
def show_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    return render_user_detail(request, db, user_id)


@router.delete("/{user_id}", response_class=HTMLResponse)
def delete_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    user_name = user.name

    db.delete(user)
    db.commit()

    return render_users(request, db, message=f"Deleted user {user_name}.")

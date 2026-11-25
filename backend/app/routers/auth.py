from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_session_user
from app.core.tokens import COOKIE_NAME, SESSION_SECONDS
from app.models import User
from app.schemas.user import Login, LoginRead, Register, UserRead
from app.services import session_service, user_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
Database = Annotated[Session, Depends(get_db)]


@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: Register, db: Database):
    return user_service.register(db, payload)


@router.post("/login", response_model=LoginRead)
def login(payload: Login, db: Database):
    return user_service.login(db, payload)


@router.post("/session", response_model=UserRead)
def open_session(payload: Login, response: Response, db: Database):
    user, token = session_service.open_session(db, payload)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=settings.environment != "local",
        samesite="strict",
        path="/",
    )
    return user


@router.get("/me", response_model=UserRead)
def me(user: Annotated[User, Depends(get_session_user)]):
    return user


@router.post("/logout", status_code=204, response_class=Response, response_model=None)
def logout(request: Request, db: Database):
    session_service.logout(db, request.cookies.get(COOKIE_NAME))
    response = Response(status_code=204)
    response.delete_cookie(COOKIE_NAME, path="/", samesite="strict")
    return response

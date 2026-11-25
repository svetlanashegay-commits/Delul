from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.tokens import COOKIE_NAME
from app.models import User
from app.repositories.user_repository import find_by_email
from app.services import session_service


def get_current_user(request: Request, db: Annotated[Session, Depends(get_db)]) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return session_service.current_user(db, token)
    # Temporary local demo identity; never use it as production authentication.
    if settings.environment != "local" or not getattr(
        settings, "allow_demo_auth", False
    ):
        raise HTTPException(401, "Sign in to continue")
    user = find_by_email(db, settings.demo_user_email)
    if user is None:
        raise HTTPException(401, "Demo user not found; run the seed first")
    return user


def get_session_user(request: Request, db: Annotated[Session, Depends(get_db)]) -> User:
    return session_service.current_user(db, request.cookies.get(COOKIE_NAME))


def require_role(*roles: str) -> Callable:
    def check(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Operation is not allowed for this role")
        return user

    return check

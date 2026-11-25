from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import User
from app.repositories.user_repository import find_by_email


def get_current_user(db: Annotated[Session, Depends(get_db)]) -> User:
    # Temporary local demo identity; never use it as production authentication.
    if settings.environment != "local":
        raise HTTPException(401, "Demo authentication is available only in local mode")
    user = find_by_email(db, settings.demo_user_email)
    if user is None:
        raise HTTPException(401, "Demo user not found; run the seed first")
    return user


def require_role(*roles: str) -> Callable:
    def check(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Operation is not allowed for this role")
        return user

    return check

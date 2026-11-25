from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.tokens import SESSION_SECONDS, new_token, token_hash, utc
from app.repositories import session_repository, user_repository
from app.schemas.user import Login, UserRead
from app.services import user_service
from app.services.errors import UnauthorizedError
from app.services.transactions import transaction


def open_session(db: Session, payload: Login):
    user_service.login(db, payload)
    with transaction(db):
        user = user_repository.find_by_email(db, payload.email)
        token = new_token()
        session_repository.create(
            db,
            {
                "user_id": user.id,
                "token_hash": token_hash(token),
                "expires_at": datetime.now(UTC) + timedelta(seconds=SESSION_SECONDS),
            },
        )
        return UserRead.model_validate(user), token


def current_user(db: Session, token: str | None):
    if not token or len(token) > 128:
        raise UnauthorizedError("Sign in to continue")
    row = session_repository.find(db, token_hash(token))
    if row is None or utc(row[0].expires_at) <= datetime.now(UTC):
        raise UnauthorizedError("Session expired; sign in again")
    return row[1]


def logout(db: Session, token: str | None):
    if token:
        with transaction(db):
            session_repository.remove(db, token_hash(token))

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import User
from app.repositories import user_repository as repository
from app.schemas.user import UserPage, UserPatch, UserRead
from app.services.errors import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.services.transactions import transaction


def list_users(db: Session, limit: int, offset: int) -> UserPage:
    items, total = repository.list(db, limit, offset)
    return UserPage(items=items, total=total, limit=limit, offset=offset)


def get_user(db: Session, user_id: UUID) -> User:
    user = repository.get(db, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return user


def update(db: Session, user_id: UUID, payload: UserPatch, actor: User) -> UserRead:
    if settings.auth_mode == "keycloak" and payload.role is not None:
        raise BadRequestError("Manage roles in Keycloak, not in the local profile")
    with transaction(db):
        user = get_user(db, user_id)
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if user_id == actor.id and "role" in changes:
            raise BadRequestError("You cannot change your own role")
        new_role = changes.get("role", user.role)
        if new_role == "student" and not changes.get("group_name", user.group_name):
            raise ValidationError("Student group_name is required")
        if new_role != user.role and (
            repository.has_quizzes(db, user_id) or repository.has_attempts(db, user_id)
        ):
            raise ConflictError("Role is referenced by existing quizzes or attempts")
        for key, value in changes.items():
            setattr(user, key, value)
        return UserRead.model_validate(repository.save(db, user))


def remove(db: Session, user_id: UUID, actor: User) -> None:
    with transaction(db):
        if user_id == actor.id:
            raise BadRequestError("You cannot delete yourself")
        repository.delete(db, get_user(db, user_id))

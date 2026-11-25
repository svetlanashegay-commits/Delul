from uuid import UUID

from sqlalchemy.orm import Session

from app.core.passwords import DUMMY_HASH, hash_password, needs_rehash, verify_password
from app.models import User
from app.repositories import user_repository as repository
from app.schemas.user import Login, LoginRead, Register, UserPage, UserPatch, UserRead
from app.services.errors import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.services.transactions import transaction


def register(db: Session, payload: Register) -> UserRead:
    with transaction(db):
        if repository.find_by_email(db, payload.email):
            raise ConflictError("Email is already registered")
        values = payload.model_dump(exclude={"password"})
        values["password_hash"] = hash_password(payload.password.get_secret_value())
        return UserRead.model_validate(repository.create(db, values))


def login(db: Session, payload: Login) -> LoginRead:
    with transaction(db):
        user = repository.find_by_email(db, payload.email)
        encoded = user.password_hash if user and user.password_hash else DUMMY_HASH
        password = payload.password.get_secret_value()
        valid = verify_password(password, encoded)
        if not valid or user is None or user.password_hash is None:
            raise UnauthorizedError("Email немесе құпиясөз қате")
        if needs_rehash(encoded):
            user.password_hash = hash_password(password)
            repository.save(db, user)
        return LoginRead(message="Credentials verified; no token or session was issued")


def list_users(db: Session, limit: int, offset: int) -> UserPage:
    items, total = repository.list(db, limit, offset)
    return UserPage(items=items, total=total, limit=limit, offset=offset)


def get_user(db: Session, user_id: UUID) -> User:
    user = repository.get(db, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return user


def update(db: Session, user_id: UUID, payload: UserPatch, actor: User) -> UserRead:
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

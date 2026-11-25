from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import DUMMY_HASH, hash_password, verify_password
from app.models import User
from app.repositories import user_repository as repository
from app.schemas.user import Login, LoginRead, Register, UserPage, UserPatch, UserRead


def register(db: Session, payload: Register) -> UserRead:
    if repository.find_by_email(db, payload.email):
        raise HTTPException(409, "Email is already registered")
    user = User(**payload.model_dump(exclude={"password"}),
                password_hash=hash_password(payload.password.get_secret_value()))
    try:
        db.add(user)
        db.flush()
        result = UserRead.model_validate(user)
        db.commit()
        return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email is already registered") from None


def login(db: Session, payload: Login) -> LoginRead:
    user = repository.find_by_email(db, payload.email)
    encoded = user.password_hash if user and user.password_hash else DUMMY_HASH
    valid = verify_password(payload.password.get_secret_value(), encoded)
    if not valid or user is None or user.password_hash is None:
        raise HTTPException(401, "Email немесе құпиясөз қате")
    return LoginRead(message="Credentials verified; no token or session was issued")


def list_users(db: Session, limit: int, offset: int) -> UserPage:
    items, total = repository.list_users(db, limit, offset)
    return UserPage(items=items, total=total, limit=limit, offset=offset)


def get_user(db: Session, user_id: UUID) -> User:
    user = repository.find(db, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


def update(db: Session, user_id: UUID, payload: UserPatch, actor: User) -> UserRead:
    user = get_user(db, user_id)
    changes = payload.model_dump(exclude_unset=True)
    if user_id == actor.id and "role" in changes:
        raise HTTPException(400, "You cannot change your own role")
    new_role = changes.get("role", user.role)
    if new_role == "student" and not changes.get("group_name", user.group_name):
        raise HTTPException(422, "Student group_name is required")
    if new_role != user.role and (
        repository.has_quizzes(db, user_id) or repository.has_attempts(db, user_id)
    ):
        raise HTTPException(409, "Role is referenced by existing quizzes or attempts")
    try:
        for key, value in changes.items():
            setattr(user, key, value)
        db.flush()
        result = UserRead.model_validate(user)
        db.commit()
        return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "User update conflicts with existing data") from None


def remove(db: Session, user_id: UUID, actor: User) -> None:
    if user_id == actor.id:
        raise HTTPException(400, "You cannot delete yourself")
    user = get_user(db, user_id)
    try:
        db.delete(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "User has quizzes or attempts and cannot be deleted") from None

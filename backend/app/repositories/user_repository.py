from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Attempt, Quiz, User


def find_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.lower()))


def get(db: Session, user_id: UUID) -> User | None:
    return db.get(User, user_id)


def list(db: Session, limit: int, offset: int):
    total = db.scalar(select(func.count()).select_from(User))
    items = db.scalars(select(User).order_by(User.id).limit(limit).offset(offset)).all()
    return items, total


def create(db: Session, values: dict) -> User:
    return save(db, User(**values))


def save(db: Session, user: User) -> User:
    db.add(user)
    db.flush()
    return user


def delete(db: Session, user: User) -> None:
    db.delete(user)
    db.flush()


def has_quizzes(db: Session, user_id: UUID) -> bool:
    return (
        db.scalar(select(Quiz.id).where(Quiz.author_id == user_id).limit(1)) is not None
    )


def has_attempts(db: Session, user_id: UUID) -> bool:
    return (
        db.scalar(select(Attempt.id).where(Attempt.user_id == user_id).limit(1))
        is not None
    )

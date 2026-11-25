from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Attempt, Quiz, User


def find_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.lower()))


def find(db: Session, user_id: UUID):
    return db.get(User, user_id)


def list_users(db: Session, limit: int, offset: int):
    total = db.scalar(select(func.count()).select_from(User))
    items = db.scalars(select(User).order_by(User.id).limit(limit).offset(offset)).all()
    return items, total


def has_quizzes(db: Session, user_id: UUID) -> bool:
    return db.scalar(select(Quiz.id).where(Quiz.author_id == user_id).limit(1)) is not None


def has_attempts(db: Session, user_id: UUID) -> bool:
    return db.scalar(select(Attempt.id).where(Attempt.user_id == user_id).limit(1)) is not None

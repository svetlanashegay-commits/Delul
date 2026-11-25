from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Attempt, Quiz, Result


def quiz_for_submission(db: Session, quiz_id: UUID):
    return db.scalar(select(Quiz).where(Quiz.id == quiz_id).with_for_update())


def my_attempts(db: Session, user_id: UUID, limit: int, offset: int):
    total = db.scalar(select(func.count()).select_from(Attempt).join(Result)
                      .where(Attempt.user_id == user_id))
    rows = db.execute(select(Attempt, Result).join(Result).where(
        Attempt.user_id == user_id,
    ).order_by(Attempt.submitted_at.desc(), Attempt.id).limit(limit).offset(offset)).all()
    return rows, total

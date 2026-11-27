from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Attempt, AttemptAnswer, Quiz, Result


def quiz_for_submission(db: Session, quiz_id: UUID):
    return db.scalar(select(Quiz).where(Quiz.id == quiz_id).with_for_update())


def my_attempts(db: Session, user_id: UUID, limit: int, offset: int):
    total = db.scalar(
        select(func.count())
        .select_from(Attempt)
        .join(Result)
        .where(Attempt.user_id == user_id)
    )
    rows = db.execute(
        select(Attempt, Result)
        .join(Result)
        .where(
            Attempt.user_id == user_id,
        )
        .order_by(Attempt.submitted_at.desc(), Attempt.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return rows, total


def save_attempt(db: Session, attempt: Attempt) -> Attempt:
    db.add(attempt)
    db.flush()
    return attempt


def save_answers_and_result(
    db: Session, attempt_id: UUID, answers: list[dict], result: Result
):
    db.add_all([AttemptAnswer(attempt_id=attempt_id, **answer) for answer in answers])
    db.add(result)
    db.flush()
    return result

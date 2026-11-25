from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Attempt, AttemptAnswer, AttemptEvent, Result, User


def get(db: Session, attempt_id: UUID):
    return db.scalar(select(Attempt).where(Attempt.id == attempt_id).with_for_update())


def existing(db: Session, quiz_id: UUID, user_id: UUID):
    return db.scalar(
        select(Attempt).where(Attempt.quiz_id == quiz_id, Attempt.user_id == user_id)
    )


def save(db: Session, attempt: Attempt):
    db.add(attempt)
    db.flush()
    return attempt


def answers(db: Session, attempt_id: UUID):
    return db.scalars(
        select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt_id)
    ).all()


def save_answers(db: Session, values):
    db.add_all(values)
    db.flush()


def result(db: Session, attempt_id: UUID):
    return db.scalar(select(Result).where(Result.attempt_id == attempt_id))


def save_result(db: Session, result: Result):
    db.add(result)
    db.flush()


def has_event(db: Session, attempt_id: UUID, event_id: UUID):
    return (
        db.scalar(
            select(AttemptEvent.id).where(
                AttemptEvent.attempt_id == attempt_id,
                AttemptEvent.event_id == event_id,
            )
        )
        is not None
    )


def add_event(db: Session, values: dict):
    db.add(AttemptEvent(**values))
    db.flush()


def for_student(db: Session, user_id: UUID):
    return db.scalars(
        select(Attempt)
        .where(Attempt.user_id == user_id)
        .order_by(Attempt.started_at.desc(), Attempt.id)
        .with_for_update()
    ).all()


def for_quiz(db: Session, quiz_id: UUID):
    return db.execute(
        select(Attempt, User)
        .join(User)
        .where(Attempt.quiz_id == quiz_id)
        .order_by(Attempt.started_at, Attempt.id)
        .with_for_update()
    ).all()

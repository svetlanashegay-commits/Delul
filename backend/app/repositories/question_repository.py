from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import AnswerOption, Question


def find(db: Session, question_id: UUID):
    return db.get(Question, question_id)


def next_position(db: Session, quiz_id: UUID):
    return (db.scalar(select(func.max(Question.position)).where(Question.quiz_id == quiz_id)) or 0) + 1


def options(db: Session, question_id: UUID):
    return db.scalars(select(AnswerOption).where(
        AnswerOption.question_id == question_id,
    ).order_by(AnswerOption.position)).all()


def replace_options(db: Session, question_id: UUID, values: list[str], correct_index: int):
    db.execute(delete(AnswerOption).where(AnswerOption.question_id == question_id))
    db.add_all([
        AnswerOption(question_id=question_id, text=text, is_correct=index == correct_index,
                     position=index + 1)
        for index, text in enumerate(values)
    ])


def remove(db: Session, question: Question):
    db.execute(delete(AnswerOption).where(AnswerOption.question_id == question.id))
    db.delete(question)

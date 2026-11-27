from uuid import UUID

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AnswerOption, Question


def get(db: Session, question_id: UUID):
    return db.get(Question, question_id)


def next_position(db: Session, quiz_id: UUID):
    return (
        db.scalar(
            select(func.max(Question.position)).where(Question.quiz_id == quiz_id)
        )
        or 0
    ) + 1


def options(db: Session, question_id: UUID):
    return db.scalars(
        select(AnswerOption)
        .where(
            AnswerOption.question_id == question_id,
        )
        .order_by(AnswerOption.position)
    ).all()


def replace_options(
    db: Session, question_id: UUID, values: list[str], correct_index: int
):
    db.execute(sql_delete(AnswerOption).where(AnswerOption.question_id == question_id))
    db.add_all(
        [
            AnswerOption(
                question_id=question_id,
                text=text,
                is_correct=index == correct_index,
                position=index + 1,
            )
            for index, text in enumerate(values)
        ]
    )


def delete(db: Session, question: Question):
    db.execute(sql_delete(AnswerOption).where(AnswerOption.question_id == question.id))
    db.delete(question)


def save(db: Session, question: Question) -> Question:
    db.add(question)
    db.flush()
    return question

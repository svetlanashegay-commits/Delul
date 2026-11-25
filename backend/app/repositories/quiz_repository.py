from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import AnswerOption, Attempt, Category, Question, Quiz


def list(
    db: Session,
    *,
    author_id: UUID | None = None,
    published_only: bool = False,
    include_published: bool = False,
    category_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
):
    filters = []
    if author_id is not None:
        condition = Quiz.author_id == author_id
        filters.append(
            or_(condition, Quiz.status == "published")
            if include_published
            else condition
        )
    if published_only:
        filters.append(Quiz.status == "published")
    if category_id is not None:
        filters.append(Quiz.category_id == category_id)
    total = db.scalar(select(func.count()).select_from(Quiz).where(*filters))
    items = db.scalars(
        select(Quiz).where(*filters).order_by(Quiz.id).limit(limit).offset(offset)
    ).all()
    return items, total


def get(db: Session, quiz_id: UUID, *, lock: bool = False) -> Quiz | None:
    statement = select(Quiz).where(Quiz.id == quiz_id)
    return db.scalar(statement.with_for_update() if lock else statement)


def create(db: Session, values: dict) -> Quiz:
    quiz = Quiz(**values)
    return save(db, quiz)


def save(db: Session, quiz: Quiz) -> Quiz:
    db.add(quiz)
    db.flush()
    return quiz


def delete(db: Session, quiz: Quiz) -> None:
    clear_questions(db, quiz.id)
    db.delete(quiz)
    db.flush()


def category_exists(db: Session, category_id: UUID) -> bool:
    return db.get(Category, category_id) is not None


def has_attempts(db: Session, quiz_id: UUID) -> bool:
    return (
        db.scalar(select(Attempt.id).where(Attempt.quiz_id == quiz_id).limit(1))
        is not None
    )


def questions(db: Session, quiz_id: UUID):
    return db.scalars(
        select(Question).where(Question.quiz_id == quiz_id).order_by(Question.position)
    ).all()


def options(db: Session, quiz_id: UUID):
    return db.scalars(
        select(AnswerOption)
        .join(Question)
        .where(Question.quiz_id == quiz_id)
        .order_by(Question.position, AnswerOption.position)
    ).all()


def clear_questions(db: Session, quiz_id: UUID) -> None:
    ids = select(Question.id).where(Question.quiz_id == quiz_id)
    db.execute(sql_delete(AnswerOption).where(AnswerOption.question_id.in_(ids)))
    db.execute(sql_delete(Question).where(Question.quiz_id == quiz_id))


def add_questions(db: Session, quiz_id: UUID, values: list[dict]) -> None:
    for value in values:
        question = Question(
            quiz_id=quiz_id, **{k: v for k, v in value.items() if k != "options"}
        )
        db.add(question)
        db.flush()
        db.add_all(
            [
                AnswerOption(question_id=question.id, position=index, **option)
                for index, option in enumerate(value.get("options", []), start=1)
            ]
        )
    db.flush()

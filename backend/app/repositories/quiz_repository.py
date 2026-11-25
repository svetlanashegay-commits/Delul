from uuid import UUID

from sqlalchemy import delete, func, or_, select, true
from sqlalchemy.orm import Session

from app.models import AnswerOption, Attempt, Category, Question, Quiz, User
from app.schemas.quiz import QuestionCreate


def accessible(user: User):
    if user.role == "admin":
        return true()
    if user.role == "teacher":
        return or_(Quiz.author_id == user.id, Quiz.status == "published")
    return Quiz.status == "published"


def list_quizzes(db: Session, user: User, category_id: UUID | None, limit: int, offset: int):
    filters = [accessible(user)]
    if category_id is not None:
        filters.append(Quiz.category_id == category_id)
    total = db.scalar(select(func.count()).select_from(Quiz).where(*filters))
    items = db.scalars(
        select(Quiz).where(*filters).order_by(Quiz.id).limit(limit).offset(offset)
    ).all()
    return items, total


def find_quiz(db: Session, quiz_id: UUID, user: User, *, lock: bool = False):
    statement = select(Quiz).where(Quiz.id == quiz_id)
    if lock:
        statement = statement.with_for_update()
    else:
        statement = statement.where(accessible(user))
    return db.scalar(statement)


def category_exists(db: Session, category_id: UUID) -> bool:
    return db.get(Category, category_id) is not None


def has_attempts(db: Session, quiz_id: UUID) -> bool:
    return db.scalar(select(Attempt.id).where(Attempt.quiz_id == quiz_id).limit(1)) is not None


def questions(db: Session, quiz_id: UUID):
    return db.scalars(
        select(Question).where(Question.quiz_id == quiz_id).order_by(Question.position)
    ).all()


def options(db: Session, quiz_id: UUID):
    return db.scalars(
        select(AnswerOption).join(Question).where(Question.quiz_id == quiz_id)
        .order_by(Question.position, AnswerOption.position)
    ).all()


def clear_questions(db: Session, quiz_id: UUID) -> None:
    ids = select(Question.id).where(Question.quiz_id == quiz_id)
    db.execute(delete(AnswerOption).where(AnswerOption.question_id.in_(ids)))
    db.execute(delete(Question).where(Question.quiz_id == quiz_id))


def add_questions(db: Session, quiz_id: UUID, values: list[QuestionCreate]) -> None:
    for value in values:
        question = Question(quiz_id=quiz_id, **value.model_dump(exclude={"options"}))
        db.add(question)
        db.flush()
        db.add_all([
            AnswerOption(question_id=question.id, position=index, **option.model_dump())
            for index, option in enumerate(value.options, start=1)
        ])

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Quiz, User
from app.repositories import quiz_repository as repository
from app.schemas.quiz import QuizCreate, QuizPage, QuizRead, QuizSummary, QuizUpdate
from app.services.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.services.transactions import transaction


def get_quiz(db: Session, quiz_id: UUID, user: User, *, lock: bool = False) -> Quiz:
    quiz = repository.get(db, quiz_id, lock=lock)
    if quiz is None:
        raise NotFoundError("Quiz not found")
    if lock:
        if user.role != "admin" and quiz.author_id != user.id:
            raise ForbiddenError("You cannot change another author's quiz")
    elif user.role != "admin" and not (
        quiz.status == "published"
        or (user.role == "teacher" and quiz.author_id == user.id)
    ):
        raise NotFoundError("Quiz not found")
    return quiz


def editable(db: Session, quiz: Quiz) -> None:
    if quiz.status != "draft" or repository.has_attempts(db, quiz.id):
        raise ConflictError("Only a draft without attempts can be changed or deleted")


def check_category(db: Session, category_id: UUID) -> None:
    if not repository.category_exists(db, category_id):
        raise ValidationError("Category not found")


def present(db: Session, quiz: Quiz, user: User) -> QuizRead:
    by_question = {}
    for option in repository.options(db, quiz.id):
        value = {"id": option.id, "text": option.text}
        if user.role in {"teacher", "admin"}:
            value["is_correct"] = option.is_correct
        by_question.setdefault(option.question_id, []).append(value)
    values = []
    for question in repository.questions(db, quiz.id):
        value = {
            "id": question.id,
            "text": question.text,
            "position": question.position,
            "options": by_question.get(question.id, []),
        }
        if user.role in {"teacher", "admin"}:
            value["explanation"] = question.explanation
        values.append(value)
    return QuizRead(**QuizSummary.model_validate(quiz).model_dump(), questions=values)


def list_quizzes(
    db: Session, user: User, category_id: UUID | None, limit: int, offset: int
):
    filters = {}
    if user.role == "teacher":
        filters.update(author_id=user.id, include_published=True)
    elif user.role == "student":
        filters.update(published_only=True)
    items, total = repository.list(
        db, category_id=category_id, limit=limit, offset=offset, **filters
    )
    return QuizPage(items=items, total=total, limit=limit, offset=offset)


def read(db: Session, quiz_id: UUID, user: User) -> QuizRead:
    return present(db, get_quiz(db, quiz_id, user), user)


def create(db: Session, payload: QuizCreate, user: User) -> QuizRead:
    with transaction(db):
        check_category(db, payload.category_id)
        quiz = repository.create(
            db,
            {
                "title": payload.title,
                "category_id": payload.category_id,
                "author_id": user.id,
            },
        )
        repository.add_questions(
            db, quiz.id, [q.model_dump() for q in payload.questions]
        )
        return present(db, quiz, user)


def update(db: Session, quiz_id: UUID, payload: QuizUpdate, user: User) -> QuizRead:
    with transaction(db):
        quiz = get_quiz(db, quiz_id, user, lock=True)
        editable(db, quiz)
        changes = payload.model_dump(
            exclude_unset=True, exclude_none=True, exclude={"questions"}
        )
        if "category_id" in changes:
            check_category(db, changes["category_id"])
        for key, value in changes.items():
            setattr(quiz, key, value)
        if payload.questions is not None:
            repository.clear_questions(db, quiz.id)
            repository.add_questions(
                db, quiz.id, [q.model_dump() for q in payload.questions]
            )
        repository.save(db, quiz)
        return present(db, quiz, user)


def remove(db: Session, quiz_id: UUID, user: User) -> None:
    with transaction(db):
        quiz = get_quiz(db, quiz_id, user, lock=True)
        editable(db, quiz)
        repository.delete(db, quiz)

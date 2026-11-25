from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Quiz, User
from app.repositories import quiz_repository as repository
from app.schemas.quiz import QuizCreate, QuizPage, QuizPatch, QuizRead, QuizSummary


def get_quiz(db: Session, quiz_id: UUID, user: User, *, lock: bool = False) -> Quiz:
    quiz = repository.find_quiz(db, quiz_id, user, lock=lock)
    if quiz is None:
        raise HTTPException(404, "Quiz not found")
    if lock and user.role != "admin" and quiz.author_id != user.id:
        raise HTTPException(403, "You cannot change another author's quiz")
    return quiz


def editable(db: Session, quiz: Quiz) -> None:
    if quiz.status != "draft" or repository.has_attempts(db, quiz.id):
        raise HTTPException(409, "Only a draft without attempts can be changed or deleted")


def check_category(db: Session, category_id: UUID) -> None:
    if not repository.category_exists(db, category_id):
        raise HTTPException(422, "Category not found")


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Operation conflicts with existing data") from None


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
            "id": question.id, "text": question.text, "position": question.position,
            "options": by_question.get(question.id, []),
        }
        if user.role in {"teacher", "admin"}:
            value["explanation"] = question.explanation
        values.append(value)
    return QuizRead(**QuizSummary.model_validate(quiz).model_dump(), questions=values)


def list_quizzes(db: Session, user: User, category_id: UUID | None, limit: int, offset: int):
    items, total = repository.list_quizzes(db, user, category_id, limit, offset)
    return QuizPage(items=items, total=total, limit=limit, offset=offset)


def read(db: Session, quiz_id: UUID, user: User) -> QuizRead:
    return present(db, get_quiz(db, quiz_id, user), user)


def create(db: Session, payload: QuizCreate, user: User) -> QuizRead:
    check_category(db, payload.category_id)
    quiz = Quiz(title=payload.title, category_id=payload.category_id, author_id=user.id)
    try:
        db.add(quiz)
        db.flush()
        repository.add_questions(db, quiz.id, payload.questions)
        db.flush()
        result = present(db, quiz, user)
        commit(db)
        return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Operation conflicts with existing data") from None
    except Exception:
        db.rollback()
        raise


def update(db: Session, quiz_id: UUID, payload: QuizPatch, user: User) -> QuizRead:
    quiz = get_quiz(db, quiz_id, user, lock=True)
    editable(db, quiz)
    if "category_id" in payload.model_fields_set:
        check_category(db, payload.category_id)
    try:
        for key, value in payload.model_dump(exclude_unset=True, exclude={"questions"}).items():
            setattr(quiz, key, value)
        if "questions" in payload.model_fields_set:
            repository.clear_questions(db, quiz.id)
            repository.add_questions(db, quiz.id, payload.questions)
        db.flush()
        result = present(db, quiz, user)
        commit(db)
        return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Operation conflicts with existing data") from None
    except Exception:
        db.rollback()
        raise


def remove(db: Session, quiz_id: UUID, user: User) -> None:
    quiz = get_quiz(db, quiz_id, user, lock=True)
    editable(db, quiz)
    try:
        repository.clear_questions(db, quiz.id)
        db.delete(quiz)
        commit(db)
    except Exception:
        db.rollback()
        raise

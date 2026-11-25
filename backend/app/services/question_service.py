from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Question, User
from app.repositories import question_repository as repository
from app.repositories.quiz_repository import has_attempts
from app.schemas.question import QuestionAdd, QuestionPatch
from app.schemas.quiz import OptionRead, QuestionRead
from app.services.errors import BadRequestError, ConflictError, NotFoundError
from app.services.quiz_service import get_quiz
from app.services.transactions import transaction


def check_draft(db, quiz):
    if quiz.status != "draft":
        raise BadRequestError("Questions can only be changed in a draft")
    if has_attempts(db, quiz.id):
        raise ConflictError("Quiz already has attempts")


def check_index(index: int, count: int):
    if index < 0 or index >= count:
        raise BadRequestError("correct_index is outside the options array (zero-based)")


def present(db: Session, question: Question):
    return QuestionRead(
        id=question.id,
        text=question.text,
        explanation=question.explanation,
        position=question.position,
        options=[
            OptionRead(id=o.id, text=o.text, is_correct=o.is_correct)
            for o in repository.options(db, question.id)
        ],
    )


def create(db: Session, quiz_id: UUID, payload: QuestionAdd, user: User):
    quiz = get_quiz(db, quiz_id, user, lock=True)
    check_draft(db, quiz)
    check_index(payload.correct_index, len(payload.options))
    question = Question(
        quiz_id=quiz.id,
        text=payload.text,
        explanation=payload.explanation,
        position=payload.position or repository.next_position(db, quiz.id),
    )
    with transaction(db):
        repository.save(db, question)
        repository.replace_options(
            db, question.id, payload.options, payload.correct_index
        )
        repository.save(db, question)
        result = present(db, question)
        return result


def owned_question(db: Session, question_id: UUID, user: User):
    question = repository.get(db, question_id)
    if question is None:
        raise NotFoundError("Question not found")
    quiz = get_quiz(db, question.quiz_id, user, lock=True)
    check_draft(db, quiz)
    return question


def update(db: Session, question_id: UUID, payload: QuestionPatch, user: User):
    question = owned_question(db, question_id, user)
    existing = repository.options(db, question.id)
    if payload.options is not None and payload.correct_index is None:
        raise BadRequestError("correct_index is required when replacing options")
    if payload.correct_index is not None:
        check_index(
            payload.correct_index,
            len(payload.options) if payload.options else len(existing),
        )
    with transaction(db):
        for key, value in payload.model_dump(
            exclude_unset=True, exclude_none=True, exclude={"options", "correct_index"}
        ).items():
            setattr(question, key, value)
        if payload.options is not None:
            repository.replace_options(
                db, question.id, payload.options, payload.correct_index
            )
        elif payload.correct_index is not None:
            for index, option in enumerate(existing):
                option.is_correct = index == payload.correct_index
        repository.save(db, question)
        result = present(db, question)
        return result


def remove(db: Session, question_id: UUID, user: User):
    question = owned_question(db, question_id, user)
    with transaction(db):
        repository.delete(db, question)

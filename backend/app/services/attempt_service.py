from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Attempt, Result, User
from app.repositories import attempt_repository as repository
from app.repositories import quiz_repository
from app.schemas.attempt import AttemptCreate, AttemptPage, AttemptRead
from app.services.errors import BadRequestError, NotFoundError
from app.services.quiz_service import get_quiz, present
from app.services.transactions import transaction


def publish(db: Session, quiz_id: UUID, user: User):
    quiz = get_quiz(db, quiz_id, user, lock=True)
    if quiz.status != "draft":
        raise BadRequestError("Only a draft can be published")
    questions = quiz_repository.questions(db, quiz.id)
    options = quiz_repository.options(db, quiz.id)
    if not questions:
        raise BadRequestError("Quiz must have at least one question")
    for question in questions:
        choices = [option for option in options if option.question_id == question.id]
        if len(choices) < 2 or sum(option.is_correct for option in choices) != 1:
            raise BadRequestError(
                "Every question needs two options and one correct answer"
            )
    with transaction(db):
        quiz.status = "published"
        quiz_repository.save(db, quiz)
        result = present(db, quiz, user)
        return result


def present_attempt(attempt, result):
    return AttemptRead(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        status=attempt.status,
        submitted_at=attempt.submitted_at,
        score=result.score,
        max_score=result.max_score,
    )


def submit(db: Session, quiz_id: UUID, payload: AttemptCreate, user: User):
    quiz = repository.quiz_for_submission(db, quiz_id)
    if quiz is None:
        raise NotFoundError("Quiz not found")
    if quiz.status != "published":
        raise BadRequestError("Only a published quiz accepts attempts")
    questions = quiz_repository.questions(db, quiz_id)
    question_ids = {question.id for question in questions}
    supplied_ids = [answer.question_id for answer in payload.answers]
    if not questions or len(supplied_ids) != len(questions):
        raise BadRequestError("Answer count must match the number of questions")
    if len(set(supplied_ids)) != len(supplied_ids) or set(supplied_ids) != question_ids:
        raise BadRequestError("Answer each question of this quiz exactly once")
    options = {option.id: option for option in quiz_repository.options(db, quiz_id)}
    score = 0
    for answer in payload.answers:
        if answer.answer_option_id is None:
            continue
        option = options.get(answer.answer_option_id)
        if option is None or option.question_id != answer.question_id:
            raise BadRequestError("Selected option does not belong to this question")
        score += int(option.is_correct)
    with transaction(db):
        attempt = Attempt(
            quiz_id=quiz_id,
            user_id=user.id,
            status="submitted",
            submitted_at=datetime.now(UTC),
        )
        repository.save_attempt(db, attempt)
        result = Result(attempt_id=attempt.id, score=score, max_score=len(questions))
        repository.save_answers_and_result(
            db, attempt.id, [a.model_dump() for a in payload.answers], result
        )
        response = present_attempt(attempt, result)
        return response


def mine(db: Session, user: User, limit: int, offset: int):
    rows, total = repository.my_attempts(db, user.id, limit, offset)
    return AttemptPage(
        items=[present_attempt(attempt, result) for attempt, result in rows],
        total=total,
        limit=limit,
        offset=offset,
    )

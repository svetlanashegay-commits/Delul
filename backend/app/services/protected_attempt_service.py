import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.tokens import new_token, token_hash, utc
from app.models import Attempt, AttemptAnswer, Result, User
from app.repositories import protection_repository as repository
from app.repositories import quiz_repository
from app.schemas.attempt import AnswerCreate, AttemptPage, AttemptRead
from app.schemas.protected_attempt import ProtectedRead, TeacherAttemptRead
from app.services.errors import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.services.quiz_service import get_quiz, present
from app.services.transactions import transaction

HEARTBEAT_GRACE_SECONDS = 45
FOCUS_LIMIT = 2


def now():
    return datetime.now(UTC)


def student(user: User):
    if user.role != "student":
        raise ForbiddenError("Only students can take a test")


def finish(db, attempt, status, reason=None):
    options = {
        option.id: option for option in quiz_repository.options(db, attempt.quiz_id)
    }
    score = sum(
        int(options[answer.answer_option_id].is_correct)
        for answer in repository.answers(db, attempt.id)
        if answer.answer_option_id in options
    )
    attempt.status = status
    attempt.submitted_at = now()
    attempt.blocked_reason = reason
    repository.save(db, attempt)
    if repository.result(db, attempt.id) is None:
        repository.save_result(
            db,
            Result(
                attempt_id=attempt.id,
                score=score,
                max_score=len(quiz_repository.questions(db, attempt.quiz_id)),
            ),
        )


def advance(db, attempt):
    if attempt.status != "in_progress":
        return
    if attempt.deadline_at is None:
        finish(db, attempt, "expired", "time_limit")
        return
    deadline = utc(attempt.deadline_at)
    lease_end = (
        utc(attempt.last_seen_at) + timedelta(seconds=HEARTBEAT_GRACE_SECONDS)
        if attempt.last_seen_at
        else deadline
    )
    if lease_end < deadline and now() > lease_end:
        finish(db, attempt, "blocked", "connection_lost")
    elif deadline <= now():
        finish(db, attempt, "expired", "time_limit")


def summary(db, attempt):
    result = repository.result(db, attempt.id)
    visible_score = result is not None and attempt.status in {"submitted", "expired"}
    return AttemptRead(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        status=attempt.status,
        submitted_at=utc(attempt.submitted_at) if attempt.submitted_at else None,
        deadline_at=utc(attempt.deadline_at) if attempt.deadline_at else None,
        score=result.score if visible_score else None,
        max_score=result.max_score if visible_score else None,
        focus_count=attempt.focus_count,
        blocked_reason=attempt.blocked_reason,
    )


def present_attempt(db, attempt, user, token=None, *, include_content=True):
    quiz = None
    values = []
    if attempt.status == "in_progress" and include_content:
        quiz = present(db, get_quiz(db, attempt.quiz_id, user), user)
        order = attempt.question_order or []
        by_id = {str(question.id): question for question in quiz.questions}
        quiz.questions = [by_id[key] for key in order if key in by_id]
        for question in quiz.questions:
            choices = {str(option.id): option for option in question.options}
            question.options = [
                choices[key]
                for key in (attempt.option_order or {}).get(str(question.id), [])
                if key in choices
            ]
        values = [
            AnswerCreate(
                question_id=value.question_id, answer_option_id=value.answer_option_id
            )
            for value in repository.answers(db, attempt.id)
        ]
    return ProtectedRead(
        **summary(db, attempt).model_dump(),
        attempt_token=token,
        quiz=quiz,
        answers=values,
        server_time=now(),
    )


def start(db: Session, quiz_id: UUID, user: User):
    student(user)
    with transaction(db):
        quiz = quiz_repository.get(db, quiz_id, lock=True)
        if quiz is None:
            raise NotFoundError("Quiz not found")
        if quiz.status != "published":
            raise BadRequestError("Only a published test can be started")
        if repository.existing(db, quiz_id, user.id):
            raise ConflictError("Only one attempt is allowed for this account and test")
        questions = quiz_repository.questions(db, quiz_id)
        if not questions:
            raise BadRequestError("Test has no questions")
        question_order = [str(question.id) for question in questions]
        options = quiz_repository.options(db, quiz_id)
        random = secrets.SystemRandom()
        random.shuffle(question_order)
        option_order = {}
        for question in questions:
            choices = [
                str(option.id)
                for option in options
                if option.question_id == question.id
            ]
            random.shuffle(choices)
            option_order[str(question.id)] = choices
        token = new_token()
        attempt = Attempt(
            user_id=user.id,
            quiz_id=quiz_id,
            status="in_progress",
            started_at=now(),
            deadline_at=now() + timedelta(minutes=quiz.time_limit_minutes),
            last_seen_at=now(),
            browser_token_hash=token_hash(token),
            question_order=question_order,
            option_order=option_order,
            focus_count=0,
        )
        repository.save(db, attempt)
        repository.save_answers(
            db,
            [
                AttemptAnswer(
                    attempt_id=attempt.id, question_id=q.id, answer_option_id=None
                )
                for q in questions
            ],
        )
        return present_attempt(db, attempt, user, token)


def owned(db, attempt_id, user, token):
    student(user)
    attempt = repository.get(db, attempt_id)
    if attempt is None or attempt.user_id != user.id:
        raise NotFoundError("Attempt not found")
    if (
        not token
        or len(token) > 128
        or not attempt.browser_token_hash
        or not hmac.compare_digest(
            attempt.browser_token_hash,
            token_hash(token),
        )
    ):
        raise ForbiddenError("Use the original test tab; its access key is missing")
    advance(db, attempt)
    return attempt


def read(db, attempt_id, user, token):
    with transaction(db):
        return present_attempt(db, owned(db, attempt_id, user, token), user)


def save(db, attempt_id, user, payload):
    with transaction(db):
        attempt = owned(db, attempt_id, user, payload.attempt_token)
        if attempt.status == "in_progress":
            rows = {
                answer.question_id: answer
                for answer in repository.answers(db, attempt.id)
            }
            ids = [answer.question_id for answer in payload.answers]
            if len(set(ids)) != len(ids) or not set(ids) <= rows.keys():
                raise BadRequestError(
                    "Answers must refer to distinct questions of this test"
                )
            choices = {
                option.id: option
                for option in quiz_repository.options(db, attempt.quiz_id)
            }
            for answer in payload.answers:
                option = choices.get(answer.answer_option_id)
                if answer.answer_option_id is not None and (
                    option is None or option.question_id != answer.question_id
                ):
                    raise BadRequestError(
                        "Selected option does not belong to this question"
                    )
                rows[answer.question_id].answer_option_id = answer.answer_option_id
            repository.save_answers(db, rows.values())
            attempt.last_seen_at = now()
            repository.save(db, attempt)
        return present_attempt(db, attempt, user, include_content=False)


def heartbeat(db, attempt_id, user, payload):
    with transaction(db):
        attempt = owned(db, attempt_id, user, payload.attempt_token)
        if attempt.status == "in_progress":
            attempt.last_seen_at = now()
            repository.save(db, attempt)
        return present_attempt(db, attempt, user, include_content=False)


def focus_lost(db, attempt_id, user, payload):
    with transaction(db):
        attempt = owned(db, attempt_id, user, payload.attempt_token)
        if attempt.status == "in_progress" and not repository.has_event(
            db, attempt.id, payload.event_id
        ):
            repository.add_event(
                db,
                {
                    "attempt_id": attempt.id,
                    "event_id": payload.event_id,
                    "kind": payload.kind,
                },
            )
            attempt.focus_count += 1
            repository.save(db, attempt)
            if attempt.focus_count >= FOCUS_LIMIT:
                finish(db, attempt, "blocked", "focus_lost")
        return present_attempt(db, attempt, user, include_content=False)


def submit(db, attempt_id, user, payload):
    with transaction(db):
        attempt = owned(db, attempt_id, user, payload.attempt_token)
        if attempt.status == "in_progress":
            finish(db, attempt, "submitted")
        return present_attempt(db, attempt, user, include_content=False)


def mine(db, user, limit, offset):
    student(user)
    with transaction(db):
        attempts = repository.for_student(db, user.id)
        for attempt in attempts:
            advance(db, attempt)
        return AttemptPage(
            items=[summary(db, a) for a in attempts[offset : offset + limit]],
            total=len(attempts),
            limit=limit,
            offset=offset,
        )


def teacher_attempts(db, quiz_id, user):
    if user.role not in {"teacher", "admin"}:
        raise ForbiddenError("Only the author or an administrator may review attempts")
    with transaction(db):
        get_quiz(db, quiz_id, user, lock=True)
        values = repository.for_quiz(db, quiz_id)
        for value, _ in values:
            advance(db, value)
        return [
            TeacherAttemptRead(
                **summary(db, a).model_dump(),
                user_id=a.user_id,
                full_name=u.full_name,
                group_name=u.group_name,
            )
            for a, u in values
        ]

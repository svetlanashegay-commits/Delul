from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_session_user, require_role
from app.models import User
from app.schemas.attempt import AttemptPage
from app.schemas.protected_attempt import (
    AnswersSave,
    AttemptStart,
    AttemptToken,
    FocusLost,
    ProtectedRead,
    TeacherAttemptRead,
)
from app.schemas.quiz import QuizRead
from app.services import attempt_service
from app.services import protected_attempt_service as protection

router = APIRouter(prefix="/api", tags=["attempts"])
Database = Annotated[Session, Depends(get_db)]
Editor = Annotated[User, Depends(require_role("teacher", "admin"))]
SessionUser = Annotated[User, Depends(get_session_user)]


@router.post(
    "/quizzes/{quiz_id}/publish",
    response_model=QuizRead,
    response_model_exclude_none=True,
)
def publish_quiz(quiz_id: UUID, db: Database, user: Editor):
    return attempt_service.publish(db, quiz_id, user)


@router.post(
    "/quizzes/{quiz_id}/attempts",
    response_model=ProtectedRead,
    response_model_exclude_none=True,
    status_code=201,
)
def start_attempt(
    quiz_id: UUID, payload: AttemptStart, db: Database, user: SessionUser
):
    return protection.start(db, quiz_id, user)


@router.get("/attempts/me", response_model=AttemptPage)
def my_attempts(
    db: Database,
    user: SessionUser,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return protection.mine(db, user, limit, offset)


@router.get(
    "/attempts/{attempt_id}",
    response_model=ProtectedRead,
    response_model_exclude_none=True,
)
def read_attempt(
    attempt_id: UUID,
    db: Database,
    user: SessionUser,
    token: Annotated[str | None, Header(alias="X-Attempt-Token")] = None,
):
    return protection.read(db, attempt_id, user, token)


@router.patch(
    "/attempts/{attempt_id}/answers",
    response_model=ProtectedRead,
    response_model_exclude_none=True,
)
def save_answers(
    attempt_id: UUID, payload: AnswersSave, db: Database, user: SessionUser
):
    return protection.save(db, attempt_id, user, payload)


@router.post(
    "/attempts/{attempt_id}/heartbeat",
    response_model=ProtectedRead,
    response_model_exclude_none=True,
)
def heartbeat(attempt_id: UUID, payload: AttemptToken, db: Database, user: SessionUser):
    return protection.heartbeat(db, attempt_id, user, payload)


@router.post(
    "/attempts/{attempt_id}/events",
    response_model=ProtectedRead,
    response_model_exclude_none=True,
)
def focus_lost(attempt_id: UUID, payload: FocusLost, db: Database, user: SessionUser):
    return protection.focus_lost(db, attempt_id, user, payload)


@router.post(
    "/attempts/{attempt_id}/submit",
    response_model=ProtectedRead,
    response_model_exclude_none=True,
)
def submit_attempt(
    attempt_id: UUID, payload: AttemptToken, db: Database, user: SessionUser
):
    return protection.submit(db, attempt_id, user, payload)


@router.get("/quizzes/{quiz_id}/attempts", response_model=list[TeacherAttemptRead])
def review_attempts(quiz_id: UUID, db: Database, user: Editor):
    return protection.teacher_attempts(db, quiz_id, user)

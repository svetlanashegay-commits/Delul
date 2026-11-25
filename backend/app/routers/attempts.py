from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models import User
from app.schemas.attempt import AttemptCreate, AttemptPage, AttemptRead
from app.schemas.quiz import QuizRead
from app.services import attempt_service

router = APIRouter(prefix="/api", tags=["attempts"])
Database = Annotated[Session, Depends(get_db)]
Editor = Annotated[User, Depends(require_role("teacher", "admin"))]
Student = Annotated[User, Depends(require_role("student"))]


@router.post("/quizzes/{quiz_id}/publish", response_model=QuizRead,
             response_model_exclude_none=True)
def publish_quiz(quiz_id: UUID, db: Database, user: Editor):
    return attempt_service.publish(db, quiz_id, user)


@router.post("/quizzes/{quiz_id}/attempts", response_model=AttemptRead, status_code=201)
def submit_attempt(quiz_id: UUID, payload: AttemptCreate, db: Database, user: Student):
    return attempt_service.submit(db, quiz_id, payload, user)


@router.get("/attempts/me", response_model=AttemptPage)
def my_attempts(db: Database, user: Student, limit: int = Query(20, ge=1, le=100),
                offset: int = Query(0, ge=0)):
    return attempt_service.mine(db, user, limit, offset)

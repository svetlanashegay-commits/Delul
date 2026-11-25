from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models import User
from app.schemas.quiz import QuizCreate, QuizPage, QuizRead, QuizUpdate
from app.services import quiz_service

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])
Database = Annotated[Session, Depends(get_db)]
Reader = Annotated[User, Depends(require_role("teacher", "student", "admin"))]
Teacher = Annotated[User, Depends(require_role("teacher", "admin"))]


@router.get("", response_model=QuizPage)
def list_quizzes(
    db: Database,
    user: Reader,
    category_id: UUID | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return quiz_service.list_quizzes(db, user, category_id, limit, offset)


@router.post(
    "", response_model=QuizRead, response_model_exclude_none=True, status_code=201
)
def create_quiz(payload: QuizCreate, response: Response, db: Database, user: Teacher):
    quiz = quiz_service.create(db, payload, user)
    response.headers["Location"] = f"/api/quizzes/{quiz.id}"
    return quiz


@router.get("/{quiz_id}", response_model=QuizRead, response_model_exclude_none=True)
def read_quiz(quiz_id: UUID, db: Database, user: Reader):
    return quiz_service.read(db, quiz_id, user)


@router.patch("/{quiz_id}", response_model=QuizRead, response_model_exclude_none=True)
def update_quiz(quiz_id: UUID, payload: QuizUpdate, db: Database, user: Teacher):
    return quiz_service.update(db, quiz_id, payload, user)


@router.delete(
    "/{quiz_id}", status_code=204, response_class=Response, response_model=None
)
def delete_quiz(quiz_id: UUID, db: Database, user: Teacher) -> Response:
    quiz_service.remove(db, quiz_id, user)
    return Response(status_code=204)

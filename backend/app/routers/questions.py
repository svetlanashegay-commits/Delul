from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models import User
from app.schemas.question import QuestionAdd, QuestionPatch
from app.schemas.quiz import QuestionRead
from app.services import question_service

router = APIRouter(prefix="/api", tags=["questions"])
Database = Annotated[Session, Depends(get_db)]
Editor = Annotated[User, Depends(require_role("teacher", "admin"))]


@router.post(
    "/quizzes/{quiz_id}/questions", response_model=QuestionRead, status_code=201
)
def create_question(quiz_id: UUID, payload: QuestionAdd, db: Database, user: Editor):
    return question_service.create(db, quiz_id, payload, user)


@router.patch("/questions/{question_id}", response_model=QuestionRead)
def update_question(
    question_id: UUID, payload: QuestionPatch, db: Database, user: Editor
):
    return question_service.update(db, question_id, payload, user)


@router.delete(
    "/questions/{question_id}",
    status_code=204,
    response_class=Response,
    response_model=None,
)
def delete_question(question_id: UUID, db: Database, user: Editor) -> Response:
    question_service.remove(db, question_id, user)
    return Response(status_code=204)

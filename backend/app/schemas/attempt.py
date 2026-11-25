from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.quiz import InputModel


class AnswerCreate(InputModel):
    question_id: UUID
    answer_option_id: UUID | None


class AttemptCreate(InputModel):
    answers: list[AnswerCreate]


class AttemptRead(BaseModel):
    id: UUID
    quiz_id: UUID
    status: str
    submitted_at: datetime
    score: int
    max_score: int


class AttemptPage(BaseModel):
    items: list[AttemptRead]
    total: int
    limit: int
    offset: int

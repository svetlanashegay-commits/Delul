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
    submitted_at: datetime | None = None
    score: int | None = None
    max_score: int | None = None
    deadline_at: datetime | None = None
    focus_count: int = 0
    blocked_reason: str | None = None


class AttemptPage(BaseModel):
    items: list[AttemptRead]
    total: int
    limit: int
    offset: int

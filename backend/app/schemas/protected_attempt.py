from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.attempt import AnswerCreate, AttemptRead
from app.schemas.quiz import InputModel, QuizRead


class AttemptStart(InputModel):
    accepted_rules: bool

    @model_validator(mode="after")
    def consent(self):
        if not self.accepted_rules:
            raise ValueError("Accept the test rules before starting")
        return self


class AttemptToken(InputModel):
    attempt_token: str = Field(min_length=32, max_length=128, repr=False)


class AnswersSave(AttemptToken):
    answers: list[AnswerCreate]


class FocusLost(AttemptToken):
    event_id: UUID
    kind: Literal["hidden", "blur", "fullscreen_exit", "pagehide"]


class ProtectedRead(AttemptRead):
    attempt_token: str | None = None
    quiz: QuizRead | None = None
    answers: list[AnswerCreate] = Field(default_factory=list)
    server_time: datetime


class TeacherAttemptRead(AttemptRead):
    user_id: UUID
    full_name: str
    group_name: str | None

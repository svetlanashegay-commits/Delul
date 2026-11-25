from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

TextValue = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OptionCreate(InputModel):
    text: TextValue
    is_correct: bool


class QuestionCreate(InputModel):
    text: TextValue
    explanation: TextValue
    position: int = Field(ge=1)
    options: list[OptionCreate] = Field(default_factory=list)


class QuizCreate(InputModel):
    title: TextValue
    category_id: UUID
    questions: list[QuestionCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_positions(self):
        positions = [q.position for q in self.questions]
        if len(positions) != len(set(positions)):
            raise ValueError("Question positions must be unique")
        return self


class QuizUpdate(InputModel):
    title: TextValue | None = None
    category_id: UUID | None = None
    questions: list[QuestionCreate] | None = None

    @model_validator(mode="after")
    def validate_changes(self):
        changes = self.model_dump(exclude_unset=True)
        if not changes:
            raise ValueError("Provide at least one editable field")
        if self.questions is not None:
            positions = [q.position for q in self.questions]
            if len(positions) != len(set(positions)):
                raise ValueError("Question positions must be unique")
        return self


class OptionRead(BaseModel):
    id: UUID
    text: str
    is_correct: bool | None = None


class QuestionRead(BaseModel):
    id: UUID
    text: str
    position: int
    options: list[OptionRead]
    explanation: str | None = None


class QuizSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    author_id: UUID
    category_id: UUID
    status: str
    results_released_at: datetime | None = None


class QuizRead(QuizSummary):
    questions: list[QuestionRead]


class QuizPage(BaseModel):
    items: list[QuizSummary]
    total: int
    limit: int
    offset: int

from pydantic import Field, model_validator

from app.schemas.quiz import InputModel, TextValue


class QuestionAdd(InputModel):
    text: TextValue
    options: list[TextValue] = Field(min_length=2)
    correct_index: int
    explanation: str = ""
    position: int | None = Field(default=None, ge=1)


class QuestionPatch(InputModel):
    text: TextValue | None = None
    options: list[TextValue] | None = Field(default=None, min_length=2)
    correct_index: int | None = None
    explanation: str | None = None
    position: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def require_changes(self):
        values = self.model_dump(exclude_unset=True)
        if not values:
            raise ValueError("Provide at least one editable field")
        return self

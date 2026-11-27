from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    model_validator,
)

from app.schemas.quiz import InputModel, TextValue


class UserPatch(InputModel):
    full_name: TextValue | None = None
    role: Literal["teacher", "student", "admin"] | None = None
    group_name: TextValue | None = None

    @model_validator(mode="after")
    def require_changes(self):
        values = self.model_dump(exclude_unset=True)
        if not values:
            raise ValueError("Provide at least one editable field")
        return self


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    full_name: str
    role: str
    group_name: str | None


class UserPage(BaseModel):
    items: list[UserRead]
    total: int
    limit: int
    offset: int

from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from app.schemas.quiz import InputModel, TextValue


class Register(InputModel):
    email: EmailStr
    full_name: TextValue
    password: SecretStr = Field(min_length=8, max_length=128)
    role: Literal["student"] = "student"
    group_name: TextValue | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()

    @model_validator(mode="after")
    def require_student_group(self):
        if self.role == "student" and not self.group_name:
            raise ValueError("Student group_name is required")
        return self


class Login(InputModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()


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


class LoginRead(BaseModel):
    message: str

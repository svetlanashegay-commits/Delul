from dataclasses import dataclass

from app.schemas.quiz import InputModel, TextValue


@dataclass(frozen=True)
class Identity:
    keycloak_id: str
    issuer: str
    email: str
    full_name: str
    role: str
    group_name: str | None = None


class KeycloakProfile(InputModel):
    group_name: TextValue

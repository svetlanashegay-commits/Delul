from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_keycloak_verifier, identity_from_claims
from app.models import User
from app.schemas.identity import Identity
from app.services import keycloak_service

oauth2 = OAuth2AuthorizationCodeBearer(
    authorizationUrl=settings.keycloak_issuer + "/protocol/openid-connect/auth",
    tokenUrl=settings.keycloak_issuer + "/protocol/openid-connect/token",
    scopes={"openid": "Identity", "profile": "Name", "email": "Email"},
    auto_error=False,
)


def get_verified_identity(token: Annotated[str | None, Depends(oauth2)]) -> Identity:
    if getattr(settings, "auth_mode", "local") != "keycloak":
        raise HTTPException(403, "Enable AUTH_MODE=keycloak first")
    if not token:
        raise HTTPException(
            401, "Keycloak Bearer access token is required", headers={"WWW-Authenticate": "Bearer"}
        )
    return identity_from_claims(get_keycloak_verifier().verify(token))


def keycloak_user(db: Session, token: str | None):
    return keycloak_service.resolve_user(db, get_verified_identity(token))


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    bearer: Annotated[str | None, Depends(oauth2)],
) -> User:
    return keycloak_user(db, bearer)


get_session_user = get_current_user


def require_role(*roles: str) -> Callable:
    def check(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Operation is not allowed for this role")
        return user

    return check

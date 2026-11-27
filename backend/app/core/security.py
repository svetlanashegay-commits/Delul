"""Strict verification of access tokens from one configured Keycloak realm."""

from functools import lru_cache

import jwt
from jwt import PyJWKClient

from app.core.config import settings
from app.schemas.identity import Identity
from app.services.errors import ForbiddenError, ServiceUnavailableError, UnauthorizedError

APP_ROLES = ("admin", "teacher", "student")


class KeycloakVerifier:
    def __init__(self, issuer: str, jwks_url: str, audience: str):
        self.issuer = issuer
        self.audience = audience
        self._jwks = PyJWKClient(
            jwks_url, cache_keys=True, cache_jwk_set=True, lifespan=300, timeout=5
        )

    def verify(self, token: str) -> dict:
        try:
            if not token or len(token) > 16384:
                raise jwt.InvalidTokenError("Invalid token size")
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256":
                raise jwt.InvalidAlgorithmError("Only RS256 is accepted")
            key = self._jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.audience,
                options={"require": ["exp", "iat", "iss", "sub", "aud"]},
            )
            if claims.get("typ") != "Bearer":
                raise jwt.InvalidTokenError("An access token is required")
            return claims
        except jwt.PyJWKClientConnectionError:
            raise ServiceUnavailableError("Keycloak public keys are unavailable") from None
        except (jwt.PyJWTError, ValueError, TypeError):
            raise UnauthorizedError("Invalid or expired Keycloak access token") from None


def identity_from_claims(claims: dict) -> Identity:
    realm = claims.get("realm_access")
    roles = realm.get("roles", []) if isinstance(realm, dict) else []
    if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
        raise ForbiddenError("Token has no application role")
    role = next((role for role in APP_ROLES if role in roles), None)
    if role is None:
        raise ForbiddenError("Token has no application role")
    subject, issuer, email = claims.get("sub"), claims.get("iss"), claims.get("email")
    if not all(isinstance(value, str) and value.strip() for value in (subject, issuer, email)):
        raise UnauthorizedError("Identity claims are incomplete")
    if len(subject) > 255 or len(issuer) > 512:
        raise UnauthorizedError("Identity claims are invalid")
    full_name = claims.get("name") or claims.get("preferred_username") or email
    if not isinstance(full_name, str) or not full_name.strip():
        raise UnauthorizedError("Identity name is invalid")
    group = claims.get("group_name")
    if group is not None and (not isinstance(group, str) or not group.strip()):
        group = None
    return Identity(subject, issuer, email.strip().lower(), full_name.strip(), role, group)


@lru_cache(maxsize=1)
def get_keycloak_verifier() -> KeycloakVerifier:
    return KeycloakVerifier(
        settings.keycloak_issuer, settings.keycloak_jwks_url, settings.keycloak_audience
    )


__all__ = [
    "APP_ROLES",
    "KeycloakVerifier",
    "get_keycloak_verifier",
    "identity_from_claims",
]

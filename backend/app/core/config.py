import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    database_url: str
    demo_user_email: str
    allow_demo_auth: bool
    auth_mode: str
    keycloak_issuer: str
    keycloak_jwks_url: str
    keycloak_audience: str
    keycloak_client_id: str


settings = Settings(
    app_name=os.getenv("APP_NAME", "Delul"),
    environment=os.getenv("ENVIRONMENT", "local"),
    database_url=os.getenv("DATABASE_URL", ""),
    demo_user_email=os.getenv("DEMO_USER_EMAIL", "teacher@demo.kz"),
    allow_demo_auth=os.getenv("ALLOW_DEMO_AUTH", "false").lower() == "true",
    auth_mode="keycloak",
    keycloak_issuer=os.getenv("KEYCLOAK_ISSUER", "http://localhost:8080/realms/delul"),
    keycloak_jwks_url=os.getenv(
        "KEYCLOAK_JWKS_URL",
        os.getenv("KEYCLOAK_ISSUER", "http://localhost:8080/realms/delul")
        + "/protocol/openid-connect/certs",
    ),
    keycloak_audience=os.getenv("KEYCLOAK_AUDIENCE", "delul-api"),
    keycloak_client_id=os.getenv("KEYCLOAK_CLIENT_ID", "delul-web"),
)

if settings.auth_mode not in {"local", "keycloak"}:
    raise ValueError("AUTH_MODE must be local or keycloak")

if (
    settings.auth_mode == "keycloak"
    and settings.environment != "local"
    and not all(
        url.startswith("https://") for url in (settings.keycloak_issuer, settings.keycloak_jwks_url)
    )
):
    raise ValueError("Keycloak issuer and JWKS must use HTTPS outside local mode")

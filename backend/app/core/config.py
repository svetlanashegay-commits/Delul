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


settings = Settings(
    app_name=os.getenv("APP_NAME", "Delul"),
    environment=os.getenv("ENVIRONMENT", "local"),
    database_url=os.getenv("DATABASE_URL", ""),
    demo_user_email=os.getenv("DEMO_USER_EMAIL", "teacher@demo.kz"),
    allow_demo_auth=os.getenv("ALLOW_DEMO_AUTH", "false").lower() == "true",
)

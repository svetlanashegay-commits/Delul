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


settings = Settings(
    app_name=os.getenv("APP_NAME", "Delul"),
    environment=os.getenv("ENVIRONMENT", "local"),
    database_url=os.getenv("DATABASE_URL", ""),
)

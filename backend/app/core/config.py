import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str


settings = Settings(
    app_name=os.getenv("APP_NAME", "Delul"),
    environment=os.getenv("ENVIRONMENT", "local"),
)

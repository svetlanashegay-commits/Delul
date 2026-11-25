from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.health_repository import ping
from app.schemas.health import HealthRead


def read(db: Session) -> HealthRead:
    try:
        ping(db)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, "Database unavailable") from None
    return HealthRead(status="ok", environment=settings.environment, database="ok")

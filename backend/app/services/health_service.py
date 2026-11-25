from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.health_repository import ping
from app.repositories.unit_of_work import transaction
from app.schemas.health import HealthRead
from app.services.errors import ServiceUnavailableError


def read(db: Session) -> HealthRead:
    try:
        with transaction(db):
            ping(db)
    except SQLAlchemyError:
        raise ServiceUnavailableError("Database unavailable") from None
    return HealthRead(status="ok", environment=settings.environment, database="ok")

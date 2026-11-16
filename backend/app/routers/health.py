from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthRead

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthRead)
def read_health() -> HealthRead:
    return HealthRead(status="ok", environment=settings.environment)

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.health import HealthRead
from app.services import health_service

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthRead)
def read_health(db: Annotated[Session, Depends(get_db)]) -> HealthRead:
    return health_service.read(db)

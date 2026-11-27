from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.config import settings

router = APIRouter()


@router.get("/test", include_in_schema=False)
def test_page():
    return FileResponse(Path(__file__).resolve().parents[1] / "web/index.html")


@router.get("/test-config", include_in_schema=False)
def test_config():
    return {"issuer": settings.keycloak_issuer, "client_id": settings.keycloak_client_id}

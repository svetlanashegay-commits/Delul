from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/test", include_in_schema=False)
def test_page():
    return FileResponse(Path(__file__).resolve().parents[1] / "web/index.html")

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.routers.attempts import router as attempts_router
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.questions import router as questions_router
from app.routers.quizzes import router as quizzes_router
from app.routers.users import router as users_router

app = FastAPI(
    title=settings.app_name,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)
app.include_router(health_router)
app.include_router(quizzes_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(questions_router)
app.include_router(attempts_router)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # Never echo passwords or request bodies in validation responses.
    detail = [{key: value for key, value in error.items() if key not in {"input", "ctx"}}
              for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": detail})

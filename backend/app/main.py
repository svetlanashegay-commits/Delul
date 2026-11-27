from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers.attempts import router as attempts_router
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.questions import router as questions_router
from app.routers.quizzes import router as quizzes_router
from app.routers.users import router as users_router
from app.routers.web import router as web_router
from app.services.errors import (
    BadRequestError,
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
    ValidationError,
)

app = FastAPI(
    title=settings.app_name,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
    swagger_ui_oauth2_redirect_url="/api/docs/oauth2-redirect",
    swagger_ui_init_oauth={
        "clientId": settings.keycloak_client_id,
        "usePkceWithAuthorizationCodeGrant": True,
        "scopes": "openid profile email",
    },
)
app.include_router(health_router)
app.include_router(quizzes_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(questions_router)
app.include_router(attempts_router)
app.include_router(web_router)
app.mount(
    "/test-assets",
    StaticFiles(directory=Path(__file__).parent / "web"),
    name="test-assets",
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith(("/api/", "/test")):
        response.headers["Cache-Control"] = "no-store"
    if request.url.path.startswith("/test"):
        response.headers["Content-Security-Policy"] = (
            f"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self' {settings.keycloak_issuer.split('/realms/')[0]}; "
            "img-src 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'"
        )
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), display-capture=()"
    return response


ERROR_STATUS = {
    BadRequestError: 400,
    UnauthorizedError: 401,
    ForbiddenError: 403,
    NotFoundError: 404,
    ConflictError: 409,
    ValidationError: 422,
    ServiceUnavailableError: 503,
}


@app.exception_handler(DomainError)
async def domain_error(request: Request, exc: DomainError):
    status = ERROR_STATUS.get(type(exc), 500)
    message = str(exc) if status != 500 else "Internal server error"
    headers = (
        {"WWW-Authenticate": "Bearer"}
        if status == 401 and settings.auth_mode == "keycloak"
        else None
    )
    return JSONResponse(status_code=status, content={"detail": message}, headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # Never echo passwords or request bodies in validation responses.
    detail = [
        {key: value for key, value in error.items() if key not in {"input", "ctx"}}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": detail})

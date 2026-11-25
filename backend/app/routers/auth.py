from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import Login, LoginRead, Register, UserRead
from app.services import user_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
Database = Annotated[Session, Depends(get_db)]


@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: Register, db: Database):
    return user_service.register(db, payload)


@router.post("/login", response_model=LoginRead)
def login(payload: Login, db: Database):
    return user_service.login(db, payload)

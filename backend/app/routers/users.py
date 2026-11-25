from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models import User
from app.schemas.user import UserPage, UserPatch, UserRead
from app.services import user_service

router = APIRouter(prefix="/api/users", tags=["users"])
Database = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_role("admin"))]


@router.get("", response_model=UserPage)
def list_users(db: Database, user: Admin, limit: int = Query(20, ge=1, le=100),
               offset: int = Query(0, ge=0)):
    return user_service.list_users(db, limit, offset)


@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: UUID, db: Database, user: Admin):
    return user_service.get_user(db, user_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: UUID, payload: UserPatch, db: Database, user: Admin):
    return user_service.update(db, user_id, payload, user)


@router.delete("/{user_id}", status_code=204, response_class=Response, response_model=None)
def delete_user(user_id: UUID, db: Database, user: Admin) -> Response:
    user_service.remove(db, user_id, user)
    return Response(status_code=204)

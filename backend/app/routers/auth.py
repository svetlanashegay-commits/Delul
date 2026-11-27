from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.get("/me", response_model=UserRead)
def me(user: Annotated[User, Depends(get_current_user)]):
    return user

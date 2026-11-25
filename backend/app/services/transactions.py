from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.unit_of_work import transaction as database_transaction
from app.services.errors import ConflictError


@contextmanager
def transaction(db: Session) -> Generator[None, None, None]:
    try:
        with database_transaction(db):
            yield
    except IntegrityError:
        raise ConflictError("Operation conflicts with existing data") from None

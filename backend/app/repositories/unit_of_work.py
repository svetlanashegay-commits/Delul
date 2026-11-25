from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session


@contextmanager
def transaction(db: Session) -> Generator[None, None, None]:
    """Also works after a dependency has started SQLAlchemy's implicit transaction."""
    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise

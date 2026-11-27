from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AuthSession, User


def find(db: Session, digest: str):
    return db.execute(
        select(AuthSession, User)
        .join(User)
        .where(
            AuthSession.token_hash == digest,
        )
    ).first()


def create(db: Session, values: dict):
    session = AuthSession(**values)
    db.add(session)
    db.flush()
    return session


def remove(db: Session, digest: str):
    db.execute(delete(AuthSession).where(AuthSession.token_hash == digest))


def revoke_user(db: Session, user_id):
    db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))

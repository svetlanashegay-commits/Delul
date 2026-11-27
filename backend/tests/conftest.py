import os
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

# Tests must never use the developer's PostgreSQL or credentials from .env.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from app.core import deps
from app.core.database import Base, get_db
from app.main import app
from app.models import User
from seed import seed


@pytest.fixture
def demo(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)  # Only this isolated, disposable test database.
    with Session(engine, expire_on_commit=False) as db:
        seed(db)
        identity = SimpleNamespace(
            environment="local", demo_user_email="teacher@demo.kz", allow_demo_auth=True
        )
        monkeypatch.setattr(deps, "settings", identity)

        def override_db():
            yield db

        def test_identity():
            if not identity.allow_demo_auth or identity.environment != "local":
                raise HTTPException(401, "Test identity disabled")
            user = db.scalar(select(User).where(User.email == identity.demo_user_email))
            if user is None:
                raise HTTPException(401, "Unknown test identity")
            return user

        app.dependency_overrides[deps.get_current_user] = test_identity
        app.dependency_overrides[get_db] = override_db
        try:
            with TestClient(app) as client:
                yield client, db, identity
        finally:
            app.dependency_overrides.clear()
    engine.dispose()

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models import User
from app.services import user_service
from app.services.errors import NotFoundError


def test_user_update_ignores_null_and_missing_fields(demo):
    client, db, identity = demo
    identity.demo_user_email = "admin@demo.kz"
    student = db.scalar(select(User).where(User.role == "student"))
    response = client.patch(
        f"/api/users/{student.id}",
        json={
            "full_name": "Updated",
            "role": None,
            "group_name": None,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated"
    assert data["role"] == "student" and data["group_name"] == "DEMO-1"


def test_service_not_found_is_independent_of_http(demo):
    _, db, _ = demo
    with pytest.raises(NotFoundError) as caught:
        user_service.get_user(db, uuid4())
    assert not hasattr(caught.value, "status_code")

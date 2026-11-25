import hashlib
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.passwords import hash_password, verify_password
from app.models import User
from app.services import user_service
from app.services.errors import NotFoundError


def test_registration_stores_only_argon2id(demo):
    client, db, _ = demo
    password = "Register-test-123"
    response = client.post(
        "/api/auth/register",
        json={
            "email": "argon@example.com",
            "full_name": "Argon Test",
            "role": "teacher",
            "password": password,
        },
    )
    assert response.status_code == 201
    user = db.scalar(select(User).where(User.email == "argon@example.com"))
    assert user.password_hash.startswith("$argon2id$")
    assert verify_password(password, user.password_hash)
    assert hash_password(password) != user.password_hash
    assert password not in response.text and "password_hash" not in response.text
    assert (
        client.post(
            "/api/auth/register",
            json={
                "email": user.email,
                "full_name": "Duplicate",
                "role": "teacher",
                "password": password,
            },
        ).status_code
        == 409
    )


def test_old_pbkdf2_hash_is_upgraded_after_successful_login(demo):
    client, db, _ = demo
    salt = bytes.fromhex("11" * 16)
    password = "Legacy-pass-123"
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000).hex()
    user = User(
        email="legacy@example.com",
        full_name="Legacy",
        role="teacher",
        password_hash=f"pbkdf2_sha256$600000${salt.hex()}${digest}",
    )
    db.add(user)
    db.commit()
    assert (
        client.post(
            "/api/auth/login",
            json={
                "email": user.email,
                "password": "incorrect",
            },
        ).status_code
        == 401
    )
    assert user.password_hash.startswith("pbkdf2_sha256$")
    assert (
        client.post(
            "/api/auth/login",
            json={
                "email": user.email,
                "password": password,
            },
        ).status_code
        == 200
    )
    assert user.password_hash.startswith("$argon2id$")


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

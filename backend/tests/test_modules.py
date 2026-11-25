from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.security import hash_password, verify_password
from app.models import Category, Quiz, User


def registration(**changes):
    return {
        "email": "new@example.com",
        "full_name": "New Student",
        "password": "test-pass-123",
        "role": "student",
        "group_name": "A-1",
        **changes,
    }


def test_register_login_and_password_not_exposed(demo):
    client, db, _ = demo
    body = registration()
    response = client.post("/api/auth/register", json=body)
    assert response.status_code == 201
    assert "password" not in response.text
    assert (
        client.post(
            "/api/auth/register", json=registration(email="NEW@example.com")
        ).status_code
        == 409
    )
    user = db.scalar(select(User).where(User.email == body["email"]))
    assert user.password_hash != body["password"]
    assert verify_password(body["password"], user.password_hash)
    login = {"email": body["email"], "password": body["password"]}
    response = client.post("/api/auth/login", json=login)
    assert response.status_code == 200
    assert set(response.json()) == {"message"}
    assert "set-cookie" not in response.headers
    for email in (body["email"], "missing@example.com", "teacher@demo.kz"):
        response = client.post(
            "/api/auth/login", json={"email": email, "password": "incorrect"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Email немесе құпиясөз қате"


@pytest.mark.parametrize(
    "changes",
    [
        {"password": "q7!x"},
        {"role": "admin"},
        {"email": "invalid"},
        {"group_name": None},
    ],
)
def test_registration_rejects_invalid_without_echoing_password(demo, changes):
    client, _, _ = demo
    data = registration(**changes)
    response = client.post("/api/auth/register", json=data)
    assert response.status_code == 422
    assert data["password"] not in response.text


def test_password_salts_and_invalid_hashes():
    first = hash_password("same-password")
    second = hash_password("same-password")
    assert first != second
    assert not verify_password("wrong", first)
    assert not verify_password("same-password", "broken")


def test_users_admin_only_self_protection_and_crud(demo):
    client, db, identity = demo
    for email in ("teacher@demo.kz", "student@demo.kz"):
        identity.demo_user_email = email
        assert client.get("/api/users").status_code == 403
    identity.demo_user_email = "admin@demo.kz"
    admin = db.scalar(select(User).where(User.role == "admin"))
    assert (
        client.patch(f"/api/users/{admin.id}", json={"role": "teacher"}).status_code
        == 400
    )
    assert client.delete(f"/api/users/{admin.id}").status_code == 400
    response = client.post("/api/auth/register", json=registration())
    path = f"/api/users/{response.json()['id']}"
    assert client.get("/api/users?limit=1").json()["total"] == 4
    assert "password" not in client.get("/api/users").text
    assert client.get(path).status_code == 200
    response = client.patch(path, json={"full_name": "Updated", "role": "teacher"})
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated"
    response = client.delete(path)
    assert response.status_code == 204 and not response.content
    assert client.get(path).status_code == 404
    assert client.get(f"/api/users/{uuid4()}").status_code == 404
    teacher = db.scalar(select(User).where(User.email == "teacher@demo.kz"))
    assert client.delete(f"/api/users/{teacher.id}").status_code == 409
    assert (
        client.patch(f"/api/users/{teacher.id}", json={"role": "admin"}).status_code
        == 409
    )


def question(**changes):
    return {
        "text": "Second question",
        "options": ["Wrong", "Correct"],
        "correct_index": 1,
        **changes,
    }


def test_question_crud_index_bounds_and_foreign_ownership(demo):
    client, db, identity = demo
    quiz_id = str(db.scalar(select(Quiz.id)))
    base = f"/api/quizzes/{quiz_id}/questions"
    for index in (-1, 2, 100):
        assert client.post(base, json=question(correct_index=index)).status_code == 400
    response = client.post(base, json=question())
    assert response.status_code == 201
    data = response.json()
    assert [o["is_correct"] for o in data["options"]] == [False, True]
    path = f"/api/questions/{data['id']}"
    assert client.patch(path, json={"options": ["A", "B"]}).status_code == 400
    response = client.patch(path, json={"options": ["A", "B"], "correct_index": 0})
    assert response.status_code == 200
    assert [o["is_correct"] for o in response.json()["options"]] == [True, False]
    response = client.patch(path, json={"correct_index": 1, "text": "Changed"})
    assert response.status_code == 200
    assert response.json()["text"] == "Changed"
    db.add(User(email="other@demo.kz", full_name="Other", role="teacher"))
    db.commit()
    identity.demo_user_email = "other@demo.kz"
    assert client.patch(path, json={"text": "Forbidden"}).status_code == 403
    assert client.delete(path).status_code == 403
    assert client.post(base, json=question()).status_code == 403
    identity.demo_user_email = "student@demo.kz"
    assert client.post(base, json=question()).status_code == 403
    identity.demo_user_email = "admin@demo.kz"
    response = client.delete(path)
    assert response.status_code == 204 and not response.content
    assert client.delete(path).status_code == 404


def test_visibility_matrix_and_admin_editor(demo):
    client, db, identity = demo
    original = db.scalar(select(Quiz))
    db.add(User(email="other@demo.kz", full_name="Other", role="teacher"))
    db.commit()
    other = db.scalar(select(User).where(User.email == "other@demo.kz"))
    db.add(
        Quiz(title="Other draft", author_id=other.id, category_id=original.category_id)
    )
    db.add(
        Quiz(
            title="Other published",
            author_id=other.id,
            category_id=original.category_id,
            status="published",
        )
    )
    db.commit()
    assert client.get("/api/quizzes").json()["total"] == 2
    identity.demo_user_email = "student@demo.kz"
    assert client.get("/api/quizzes").json()["total"] == 1
    identity.demo_user_email = "admin@demo.kz"
    assert client.get("/api/quizzes").json()["total"] == 3
    assert (
        client.patch(
            f"/api/quizzes/{original.id}", json={"title": "Admin edit"}
        ).status_code
        == 200
    )
    category_id = str(db.scalar(select(Category.id)))
    assert (
        client.post(
            "/api/quizzes", json={"title": "Admin quiz", "category_id": category_id}
        ).status_code
        == 201
    )


def test_health_database_success_and_failure(demo, monkeypatch):
    client, _, _ = demo
    assert client.get("/api/health").json()["database"] == "ok"
    from app.services import health_service

    def fail(db):
        raise SQLAlchemyError("secret connection details")

    monkeypatch.setattr(health_service, "ping", fail)
    response = client.get("/api/health")
    assert response.status_code == 503
    assert "secret" not in response.text

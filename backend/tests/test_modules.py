
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models import Category, Quiz, User


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

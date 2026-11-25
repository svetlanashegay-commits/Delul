from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models import AnswerOption, Attempt, Category, Question, Quiz, User
from seed import seed


def payload(db):
    return {
        "title": "New quiz",
        "category_id": str(db.scalar(select(Category.id))),
        "questions": [
            {
                "text": "Question",
                "explanation": "Explanation",
                "position": 1,
                "options": [
                    {"text": "Yes", "is_correct": True},
                    {"text": "No", "is_correct": False},
                ],
            }
        ],
    }


def test_crud_and_question_replacement(demo):
    client, db, _ = demo
    response = client.post("/api/quizzes", json=payload(db))
    assert response.status_code == 201
    quiz = response.json()
    path = response.headers["location"]
    assert path == f"/api/quizzes/{quiz['id']}"
    assert quiz["status"] == "draft"
    assert quiz["questions"][0]["options"][0]["is_correct"] in (True, False)
    old_question = quiz["questions"][0]["id"]
    assert client.get(path).status_code == 200
    assert client.get("/api/quizzes?limit=1&offset=0").json()["total"] == 2
    replacement = payload(db)
    replacement["title"] = "Updated"
    response = client.patch(path, json=replacement)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"
    assert response.json()["questions"][0]["id"] != old_question
    response = client.delete(path)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(path).status_code == 404
    assert db.scalar(select(func.count()).select_from(Question)) == 1
    assert db.scalar(select(func.count()).select_from(AnswerOption)) == 2


def test_student_visibility_and_mutation_denied(demo):
    client, db, identity = demo
    quiz = db.scalar(select(Quiz))
    path = f"/api/quizzes/{quiz.id}"
    identity.demo_user_email = "student@demo.kz"
    assert client.get("/api/quizzes").json()["total"] == 0
    assert client.get(path).status_code == 404
    quiz.status = "published"
    db.commit()
    response = client.get(path)
    assert response.status_code == 200
    question = response.json()["questions"][0]
    assert "explanation" not in question
    assert all("is_correct" not in option for option in question["options"])
    assert client.get("/api/quizzes").json()["total"] == 1
    assert client.post("/api/quizzes", json=payload(db)).status_code == 403
    assert client.patch(path, json={"title": "Forbidden"}).status_code == 403
    assert client.delete(path).status_code == 403


def test_other_teacher_cannot_access_or_change(demo):
    client, db, identity = demo
    path = f"/api/quizzes/{db.scalar(select(Quiz.id))}"
    db.add(User(email="other@demo.kz", full_name="Other", role="teacher"))
    db.commit()
    identity.demo_user_email = "other@demo.kz"
    assert client.get("/api/quizzes").json()["total"] == 0
    assert client.get(path).status_code == 404
    assert client.patch(path, json={"title": "Forbidden"}).status_code == 403
    assert client.delete(path).status_code == 403


@pytest.mark.parametrize("status,with_attempt", [("published", False), ("draft", True)])
def test_immutable_quiz(demo, status, with_attempt):
    client, db, _ = demo
    quiz = db.scalar(select(Quiz))
    quiz.status = status
    if with_attempt:
        student = db.scalar(select(User).where(User.role == "student"))
        db.add(Attempt(quiz_id=quiz.id, user_id=student.id))
    db.commit()
    path = f"/api/quizzes/{quiz.id}"
    assert client.patch(path, json={"title": "Forbidden"}).status_code == 409
    assert client.delete(path).status_code == 409
    assert client.get(path).json()["title"] == "Demo quiz"


def test_demo_identity_and_admin_permissions(demo):
    client, _, identity = demo
    identity.demo_user_email = "missing@demo.kz"
    assert client.get("/api/quizzes").status_code == 401
    identity.demo_user_email = "admin@demo.kz"
    assert client.get("/api/quizzes").status_code == 200
    identity.demo_user_email = "teacher@demo.kz"
    identity.environment = "production"
    assert client.get("/api/quizzes").status_code == 401


def test_validation_and_missing_resources(demo):
    client, db, _ = demo
    path = f"/api/quizzes/{db.scalar(select(Quiz.id))}"
    for body in [{}, {"title": "  "}, {"status": "published"}]:
        assert client.patch(path, json=body).status_code == 422
    before = client.get(path).json()
    response = client.patch(
        path, json={"title": None, "category_id": None, "questions": None}
    )
    assert response.status_code == 200
    assert response.json() == before
    data = payload(db)
    data["questions"] *= 2
    assert client.post("/api/quizzes", json=data).status_code == 422
    data = payload(db)
    data["category_id"] = str(uuid4())
    assert client.post("/api/quizzes", json=data).status_code == 422
    assert client.get("/api/quizzes?limit=0").status_code == 422
    assert client.get("/api/quizzes/invalid").status_code == 422
    assert client.delete(f"/api/quizzes/{uuid4()}").status_code == 404
    assert client.get("/api/quizzes").json()["total"] == 1


def test_nested_create_rolls_back_on_failure(demo, monkeypatch):
    client, db, _ = demo
    from app.repositories import quiz_repository

    def fail(*args):
        raise RuntimeError("Simulated failure")

    monkeypatch.setattr(quiz_repository, "add_questions", fail)
    with pytest.raises(RuntimeError, match="Simulated failure"):
        client.post("/api/quizzes", json=payload(db))
    assert db.scalar(select(func.count()).select_from(Quiz)) == 1


def test_seed_is_repeatable_and_checks_existing_roles(demo):
    _, db, _ = demo
    seed(db)
    assert db.scalar(select(func.count()).select_from(User)) == 3
    assert db.scalar(select(func.count()).select_from(Quiz)) == 1
    user = db.scalar(select(User).where(User.email == "admin@demo.kz"))
    user.role = "teacher"
    db.commit()
    with pytest.raises(ValueError, match="different role"):
        seed(db)
    assert db.get(User, user.id).role == "teacher"

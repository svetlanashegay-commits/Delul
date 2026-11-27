from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.tokens import utc
from app.models import Attempt, AttemptEvent, Quiz, Result, User
from app.services import protected_attempt_service as service


@pytest.fixture
def secure(demo):
    client, db, identity = demo
    quiz_id = str(db.scalar(select(Quiz.id)))
    assert client.post(f"/api/quizzes/{quiz_id}/publish").status_code == 200
    student = db.scalar(select(User).where(User.role == "student"))
    identity.demo_user_email = student.email
    return client, db, identity, quiz_id, student.id


def start(secure):
    client, _, _, quiz_id, _ = secure
    response = client.post(
        f"/api/quizzes/{quiz_id}/attempts", json={"accepted_rules": True}
    )
    assert response.status_code == 201
    return response.json()




def test_start_requires_rules_and_real_session_and_has_no_bypass(demo):
    client, db, _ = demo
    quiz_id = str(db.scalar(select(Quiz.id)))
    _.allow_demo_auth = False
    assert (
        client.post(
            f"/api/quizzes/{quiz_id}/attempts", json={"accepted_rules": True}
        ).status_code
        == 401
    )
    assert db.scalar(select(func.count()).select_from(Attempt)) == 0


def test_one_attempt_server_constraint_and_random_order_survives_reload(secure):
    client, db, _, quiz_id, student_id = secure
    assert (
        client.post(
            f"/api/quizzes/{quiz_id}/attempts", json={"accepted_rules": False}
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/quizzes/{quiz_id}/attempts", json={"answers": []}
        ).status_code
        == 422
    )
    assert client.get(f"/api/quizzes/{quiz_id}").json()["questions"] == []
    data = start(secure)
    assert (
        client.post(
            f"/api/quizzes/{quiz_id}/attempts", json={"accepted_rules": True}
        ).status_code
        == 409
    )
    assert client.get(f"/api/attempts/{data['id']}").status_code == 403
    again = client.get(
        f"/api/attempts/{data['id']}",
        headers={"X-Attempt-Token": data["attempt_token"]},
    )
    assert again.status_code == 200
    assert again.json()["quiz"] == data["quiz"]
    assert again.json()["deadline_at"] == data["deadline_at"]
    q = data["quiz"]["questions"][0]
    assert "explanation" not in q
    assert all("is_correct" not in option for option in q["options"])
    db.add(Attempt(user_id=student_id, quiz_id=UUID(quiz_id)))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
    assert db.scalar(select(func.count()).select_from(Attempt)) == 1


def test_save_and_submit_are_atomic_and_cannot_be_repeated(secure):
    client, db, _, quiz_id, _ = secure
    data = start(secure)
    token = data["attempt_token"]
    base = f"/api/attempts/{data['id']}"
    q = data["quiz"]["questions"][0]
    wrong = {
        "attempt_token": token,
        "answers": [{"question_id": q["id"], "answer_option_id": str(uuid4())}],
    }
    assert client.patch(base + "/answers", json=wrong).status_code == 400
    body = {
        "attempt_token": token,
        "answers": [
            {"question_id": q["id"], "answer_option_id": q["options"][0]["id"]}
        ],
    }
    assert client.patch(base + "/answers", json=body).status_code == 200
    response = client.post(base + "/submit", json={"attempt_token": token})
    assert response.status_code == 200 and response.json()["status"] == "submitted"
    assert response.json()["max_score"] == 1
    assert "quiz" not in response.json()
    repeated = client.post(base + "/submit", json={"attempt_token": token}).json()
    for key in ("id", "status", "score", "max_score", "submitted_at"):
        assert repeated[key] == response.json()[key]
    assert db.scalar(select(func.count()).select_from(Result)) == 1
    assert client.patch(base + "/answers", json=wrong).json()["status"] == "submitted"
    assert (
        client.post(
            f"/api/quizzes/{quiz_id}/attempts", json={"accepted_rules": True}
        ).status_code
        == 409
    )


def test_first_focus_warns_duplicate_is_ignored_second_blocks(secure):
    client, db, identity, _, _ = secure
    data = start(secure)
    base = f"/api/attempts/{data['id']}"
    body = {
        "attempt_token": data["attempt_token"],
        "event_id": str(uuid4()),
        "kind": "hidden",
    }
    response = client.post(base + "/events", json=body)
    assert response.json()["focus_count"] == 1
    assert response.json()["status"] == "in_progress"
    assert client.post(base + "/events", json=body).json()["focus_count"] == 1
    body["event_id"] = str(uuid4())
    response = client.post(base + "/events", json=body)
    assert response.json()["status"] == "blocked"
    assert response.json()["blocked_reason"] == "focus_lost"
    assert "quiz" not in response.json() and "score" not in response.json()
    assert db.scalar(select(func.count()).select_from(AttemptEvent)) == 2
    assert (
        client.post(
            base + "/heartbeat", json={"attempt_token": data["attempt_token"]}
        ).json()["status"]
        == "blocked"
    )


def test_server_deadline_and_heartbeat_are_authoritative(secure, monkeypatch):
    client, db, _, _, _ = secure
    fixed = datetime.now(UTC)
    monkeypatch.setattr(service, "now", lambda: fixed)
    db.scalar(select(Quiz)).time_limit_minutes = 1
    db.commit()
    data = start(secure)
    base = f"/api/attempts/{data['id']}"
    key = {"attempt_token": data["attempt_token"]}
    deadline = data["deadline_at"]
    fixed += timedelta(seconds=20)
    response = client.post(base + "/heartbeat", json=key)
    assert response.json()["deadline_at"] == deadline
    fixed += timedelta(seconds=20)
    assert client.post(base + "/heartbeat", json=key).json()["status"] == "in_progress"
    fixed = utc(db.scalar(select(Attempt)).deadline_at) + timedelta(seconds=1)
    response = client.post(base + "/submit", json=key)
    assert response.json()["status"] == "expired"
    assert response.json()["score"] == 0
    assert db.scalar(select(func.count()).select_from(Result)) == 1


def test_missing_heartbeat_closes_access_permanently(secure, monkeypatch):
    client, _, _, _, _ = secure
    fixed = datetime.now(UTC)
    monkeypatch.setattr(service, "now", lambda: fixed)
    data = start(secure)
    fixed += timedelta(seconds=46)
    response = client.post(
        f"/api/attempts/{data['id']}/heartbeat",
        json={"attempt_token": data["attempt_token"]},
    )
    assert response.json()["status"] == "blocked"
    assert response.json()["blocked_reason"] == "connection_lost"
    assert client.get("/api/attempts/me").json()["items"][0]["status"] == "blocked"


def test_foreign_session_and_modified_tokens_are_rejected(secure):
    client, db, identity, _, _ = secure
    data = start(secure)
    base = f"/api/attempts/{data['id']}"
    assert (
        client.post(base + "/submit", json={"attempt_token": "x" * 43}).status_code
        == 403
    )
    other = User(
        email="otherstudent@example.com",
        full_name="Other",
        group_name="B",
        role="student",
    )
    db.add(other)
    db.commit()
    identity.demo_user_email = other.email
    assert (
        client.post(
            base + "/submit", json={"attempt_token": data["attempt_token"]}
        ).status_code
        == 404
    )
    assert client.get("/api/attempts/me").json()["total"] == 0


def test_web_page_and_assets_have_restrictive_headers(demo):
    client, _, _ = demo
    response = client.get("/test")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert "camera=()" in response.headers["permissions-policy"]
    assert client.get("/test-assets/test.js").status_code == 200
    assert client.get("/test-assets/test.css").status_code == 200


def test_completion_failure_rolls_back_status_and_result(secure, monkeypatch):
    client, db, _, _, _ = secure
    data = start(secure)

    def fail():
        raise RuntimeError("Simulated commit failure")

    monkeypatch.setattr(db, "commit", fail)
    with pytest.raises(RuntimeError, match="Simulated commit failure"):
        client.post(
            f"/api/attempts/{data['id']}/submit",
            json={"attempt_token": data["attempt_token"]},
        )
    assert db.scalar(select(Attempt)).status == "in_progress"
    assert db.scalar(select(func.count()).select_from(Result)) == 0


def test_author_reviews_attempts_but_other_users_cannot(secure):
    client, db, identity, quiz_id, _ = secure
    data = start(secure)
    assert client.get(f"/api/quizzes/{quiz_id}/attempts").status_code == 403
    client.post("/api/auth/logout")
    identity.demo_user_email = "teacher@demo.kz"
    response = client.get(f"/api/quizzes/{quiz_id}/attempts")
    assert response.status_code == 200
    assert response.json()[0]["id"] == data["id"]
    assert response.json()[0]["full_name"] == "Demo Student"
    assert (
        "browser_token_hash" not in response.text
        and "attempt_token" not in response.text
    )
    db.add(User(email="outsider@example.com", full_name="Other", role="teacher"))
    db.commit()
    identity.demo_user_email = "outsider@example.com"
    assert client.get(f"/api/quizzes/{quiz_id}/attempts").status_code == 403




def test_leaving_until_after_deadline_still_records_connection_block(
    secure, monkeypatch
):
    client, _, _, _, _ = secure
    fixed = datetime.now(UTC)
    monkeypatch.setattr(service, "now", lambda: fixed)
    data = start(secure)
    fixed += timedelta(hours=1)
    response = client.post(
        f"/api/attempts/{data['id']}/heartbeat",
        json={"attempt_token": data["attempt_token"]},
    )
    assert response.json()["status"] == "blocked"

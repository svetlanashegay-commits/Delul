"""Local demo data. Run from backend: python seed.py (after migrations)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Category, Quiz, User
from app.repositories.quiz_repository import add_questions
from app.schemas.quiz import QuestionCreate


def seed(db: Session) -> None:
    try:
        for email, name, role, group in [
            ("teacher@demo.kz", "Demo Teacher", "teacher", None),
            ("student@demo.kz", "Demo Student", "student", "DEMO-1"),
            ("admin@demo.kz", "Demo Admin", "admin", None),
        ]:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                db.add(User(email=email, full_name=name, role=role, group_name=group))
            elif user.role != role:
                raise ValueError(f"Existing demo account has a different role: {email}")
        db.flush()
        teacher = db.scalar(select(User).where(User.email == "teacher@demo.kz"))
        category = db.scalar(select(Category).where(Category.name == "Demo"))
        if category is None:
            category = Category(name="Demo", description="Demo quizzes")
            db.add(category)
            db.flush()
        quiz = db.scalar(select(Quiz).where(
            Quiz.title == "Demo quiz", Quiz.author_id == teacher.id,
            Quiz.category_id == category.id,
        ))
        if quiz is None:
            quiz = Quiz(title="Demo quiz", author_id=teacher.id, category_id=category.id)
            db.add(quiz)
            db.flush()
            add_questions(db, quiz.id, [QuestionCreate(
                text="What does a primary key identify?", position=1,
                explanation="A primary key uniquely identifies a row.",
                options=[
                    {"text": "A row", "is_correct": True},
                    {"text": "A database server", "is_correct": False},
                ],
            )])
        db.commit()
    except Exception:
        db.rollback()
        raise


if __name__ == "__main__":
    if settings.environment != "local":
        raise SystemExit("Seed is available only in local mode")
    with SessionLocal() as session:
        seed(session)
    print("Demo users and quiz are ready.")

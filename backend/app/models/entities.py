from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('teacher', 'student', 'admin')", name="ck_users_role"),
        CheckConstraint("length(trim(email)) > 0", name="ck_users_email_not_blank"),
        CheckConstraint("length(trim(full_name)) > 0", name="ck_users_full_name_not_blank"),
        CheckConstraint(
            "role <> 'student' OR (group_name IS NOT NULL AND length(trim(group_name)) > 0)",
            name="ck_users_student_group",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String, unique=True)
    full_name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    group_name: Mapped[str | None] = mapped_column(String, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Quiz(Base):
    __tablename__ = "quizzes"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'closed')", name="ck_quizzes_status"),
        CheckConstraint(
            "results_released_at IS NULL OR status = 'closed'",
            name="ck_quizzes_results_closed",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String, default="draft")
    results_released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("quiz_id", "position", name="uq_questions_quiz_position"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    quiz_id: Mapped[UUID] = mapped_column(ForeignKey("quizzes.id", ondelete="RESTRICT"))
    text: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)


class AnswerOption(Base):
    __tablename__ = "answer_options"
    __table_args__ = (
        UniqueConstraint("question_id", "position", name="uq_options_question_position"),
        CheckConstraint("position >= 1", name="ck_options_position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    question_id: Mapped[UUID] = mapped_column(ForeignKey("questions.id", ondelete="RESTRICT"))
    text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    position: Mapped[int] = mapped_column(Integer)


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = (
        CheckConstraint("status IN ('in_progress', 'submitted')", name="ck_attempts_status"),
        CheckConstraint(
            "(status = 'in_progress' AND submitted_at IS NULL) OR "
            "(status = 'submitted' AND submitted_at IS NOT NULL)",
            name="ck_attempts_submission_time",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    quiz_id: Mapped[UUID] = mapped_column(ForeignKey("quizzes.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String, default="in_progress")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_answers_attempt_question"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    attempt_id: Mapped[UUID] = mapped_column(ForeignKey("attempts.id", ondelete="RESTRICT"))
    question_id: Mapped[UUID] = mapped_column(ForeignKey("questions.id", ondelete="RESTRICT"))
    answer_option_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("answer_options.id", ondelete="RESTRICT"), nullable=True
    )


class Result(Base):
    __tablename__ = "results"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= max_score", name="ck_results_score_range"),
        CheckConstraint("max_score >= 0", name="ck_results_max_score_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey("attempts.id", ondelete="RESTRICT"), unique=True
    )
    score: Mapped[int] = mapped_column(Integer)
    max_score: Mapped[int] = mapped_column(Integer)
    graded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

"""One attempt per account, server deadlines, session cookies and focus events."""

import sqlalchemy as sa
from alembic import op

revision = "0003_protected_attempts"
down_revision = "0002_password_hash"
branch_labels = None
depends_on = None


def upgrade():
    if not op.get_context().as_sql:
        duplicates = (
            op.get_bind()
            .execute(
                sa.text(
                    "SELECT user_id, quiz_id FROM attempts GROUP BY user_id, quiz_id HAVING COUNT(*) > 1",
                )
            )
            .first()
        )
        if duplicates:
            raise RuntimeError(
                "Duplicate attempts exist. Review them before applying this migration; no data was deleted."
            )
    with op.batch_alter_table("quizzes") as batch:
        batch.add_column(
            sa.Column(
                "time_limit_minutes", sa.Integer(), nullable=False, server_default="30"
            )
        )
        batch.create_check_constraint(
            "ck_quizzes_time_limit", "time_limit_minutes BETWEEN 1 AND 180"
        )
    with op.batch_alter_table("attempts") as batch:
        batch.drop_constraint("ck_attempts_status", type_="check")
        batch.drop_constraint("ck_attempts_submission_time", type_="check")
        batch.add_column(
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            )
        )
        batch.add_column(
            sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(sa.Column("browser_token_hash", sa.String(64), nullable=True))
        batch.add_column(
            sa.Column("focus_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("blocked_reason", sa.String(), nullable=True))
        batch.add_column(sa.Column("question_order", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("option_order", sa.JSON(), nullable=True))
        batch.create_unique_constraint(
            "uq_attempts_student_quiz", ["user_id", "quiz_id"]
        )
        batch.create_check_constraint(
            "ck_attempts_status",
            "status IN ('in_progress', 'submitted', 'blocked', 'expired')",
        )
        batch.create_check_constraint(
            "ck_attempts_submission_time",
            "(status = 'in_progress' AND submitted_at IS NULL) OR "
            "(status IN ('submitted', 'blocked', 'expired') AND submitted_at IS NOT NULL)",
        )
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "attempt_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.Uuid(),
            sa.ForeignKey("attempts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("attempt_id", "event_id", name="uq_attempt_event"),
    )


def downgrade():
    op.drop_table("attempt_events")
    op.drop_table("auth_sessions")
    op.execute(
        "UPDATE attempts SET status='submitted' WHERE status IN ('blocked', 'expired')"
    )
    with op.batch_alter_table("attempts") as batch:
        batch.drop_constraint("ck_attempts_status", type_="check")
        batch.drop_constraint("ck_attempts_submission_time", type_="check")
        batch.drop_constraint("uq_attempts_student_quiz", type_="unique")
        for name in [
            "started_at",
            "deadline_at",
            "last_seen_at",
            "browser_token_hash",
            "focus_count",
            "blocked_reason",
            "question_order",
            "option_order",
        ]:
            batch.drop_column(name)
        batch.create_check_constraint(
            "ck_attempts_status", "status IN ('in_progress', 'submitted')"
        )
        batch.create_check_constraint(
            "ck_attempts_submission_time",
            "(status = 'in_progress' AND submitted_at IS NULL) OR (status = 'submitted' AND submitted_at IS NOT NULL)",
        )
    with op.batch_alter_table("quizzes") as batch:
        batch.drop_constraint("ck_quizzes_time_limit", type_="check")
        batch.drop_column("time_limit_minutes")

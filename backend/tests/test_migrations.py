import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect


def test_initial_migration_roundtrip_and_postgres_sql(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    url = f"sqlite+pysqlite:///{(tmp_path / 'migration.db').as_posix()}"
    env = dict(os.environ, DATABASE_URL=url)

    def run(*args, run_env=env):
        return subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=backend,
            env=run_env,
            check=True,
            capture_output=True,
            text=True,
        )

    run("upgrade", "head")
    engine = create_engine(url)
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {
        "alembic_version",
        "users",
        "categories",
        "quizzes",
        "questions",
        "answer_options",
        "attempts",
        "attempt_answers",
        "results",
        "auth_sessions",
        "attempt_events",
    }
    assert "password_hash" in {
        column["name"] for column in inspector.get_columns("users")
    }
    assert "position" in {
        column["name"] for column in inspector.get_columns("answer_options")
    }
    engine.dispose()
    run("check")
    run("downgrade", "base")
    engine = create_engine(url)
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()
    # Compile migration SQL for PostgreSQL, without opening any connection.
    sql = run(
        "upgrade",
        "head",
        "--sql",
        run_env=dict(
            env,
            DATABASE_URL="postgresql+psycopg://localhost/unused",
        ),
    ).stdout
    assert "CREATE TABLE users" in sql
    assert "ON DELETE RESTRICT" in sql


def test_password_revision_repairs_legacy_schema_without_losing_users(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    url = f"sqlite+pysqlite:///{(tmp_path / 'legacy.db').as_posix()}"
    env = dict(os.environ, DATABASE_URL=url)

    def run(revision):
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", revision],
            cwd=backend,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    run("d4db3a57ff91")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE users DROP COLUMN password_hash")
        connection.exec_driver_sql(
            "INSERT INTO users (id, email, full_name, role) "
            "VALUES ('11111111111141118111111111111111', 'legacy@example.com', 'Legacy', 'teacher')",
        )
    run("head")
    with engine.connect() as connection:
        assert "password_hash" in {
            c["name"] for c in inspect(connection).get_columns("users")
        }
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM users").scalar() == 1
        assert (
            connection.exec_driver_sql("SELECT password_hash FROM users").scalar()
            is None
        )
    engine.dispose()


def test_protection_migration_refuses_duplicate_history_without_deleting_it(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    url = f"sqlite+pysqlite:///{(tmp_path / 'duplicates.db').as_posix()}"
    env = dict(os.environ, DATABASE_URL=url)
    command = [sys.executable, "-m", "alembic", "upgrade"]
    subprocess.run(
        command + ["0002_password_hash"],
        cwd=backend,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO users (id,email,full_name,role,group_name) VALUES "
            "('11111111111141118111111111111111','student@example.com','Student','student','A')"
        )
        connection.exec_driver_sql(
            "INSERT INTO categories (id,name,description) VALUES "
            "('22222222222242228222222222222222','Category','Description')"
        )
        connection.exec_driver_sql(
            "INSERT INTO quizzes (id,title,author_id,category_id,status) VALUES "
            "('33333333333343338333333333333333','Legacy','11111111111141118111111111111111',"
            "'22222222222242228222222222222222','published')"
        )
        for value in [
            "44444444444444448444444444444444",
            "55555555555545558555555555555555",
        ]:
            connection.exec_driver_sql(
                "INSERT INTO attempts (id,user_id,quiz_id,status) VALUES "
                "(?, '11111111111141118111111111111111','33333333333343338333333333333333','in_progress')",
                (value,),
            )
    result = subprocess.run(
        command + ["head"], cwd=backend, env=env, capture_output=True, text=True, check=False
    )
    assert result.returncode != 0 and "Duplicate attempts exist" in result.stderr
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM attempts").scalar() == 2
        assert "auth_sessions" not in inspect(connection).get_table_names()
        assert "deadline_at" not in {
            c["name"] for c in inspect(connection).get_columns("attempts")
        }
    engine.dispose()

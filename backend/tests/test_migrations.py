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
            [sys.executable, "-m", "alembic", *args], cwd=backend, env=run_env,
            check=True, capture_output=True, text=True,
        )

    run("upgrade", "head")
    engine = create_engine(url)
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {
        "alembic_version", "users", "categories", "quizzes", "questions", "answer_options",
        "attempts", "attempt_answers", "results",
    }
    assert "password_hash" in {column["name"] for column in inspector.get_columns("users")}
    assert "position" in {column["name"] for column in inspector.get_columns("answer_options")}
    engine.dispose()
    run("check")
    run("downgrade", "base")
    engine = create_engine(url)
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()
    # Compile migration SQL for PostgreSQL, without opening any connection.
    sql = run("upgrade", "head", "--sql", run_env=dict(
        env, DATABASE_URL="postgresql+psycopg://localhost/unused",
    )).stdout
    assert "CREATE TABLE users" in sql
    assert "ON DELETE RESTRICT" in sql

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "quizai-db"
VOLUME = "quizai-pgdata"


def docker(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(["docker", *args], cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Docker command failed")
    return result


def main() -> None:
    print("Checking Docker Engine...", flush=True)
    docker("info", "--format", "{{.ServerVersion}}")
    if not (ROOT / ".env").is_file():
        raise RuntimeError("Local .env is missing next to this script.")
    existing = docker("container", "inspect", NAME, check=False)
    if existing.returncode:
        # Distinguish a missing container from an inaccessible Docker Engine.
        docker("info", "--format", "{{.ServerVersion}}")
        current = None
    else:
        current = json.loads(existing.stdout)[0]
    if current and current["Config"]["Image"] != "postgres:18-alpine":
        raise RuntimeError("quizai-db uses another image. It was left unchanged.")
    if current and not current["State"]["Running"]:
        backup = NAME + "-saved-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        docker("rename", NAME, backup)
        print("Preserved stopped container as " + backup, flush=True)
        current = None
    if current is None:
        users = docker("ps", "--filter", "volume=" + VOLUME, "--format", "{{.Names}}").stdout.strip()
        if users:
            raise RuntimeError("The volume is already in use by: " + users + ". Nothing was deleted.")
        print("Creating PostgreSQL with an automatically assigned localhost port...", flush=True)
        result = docker("run", "-d", "--name", NAME, "--env-file", ".env",
                        "-p", "127.0.0.1::5432", "-v", VOLUME + ":/var/lib/postgresql",
                        "postgres:18-alpine")
        print("Created container " + result.stdout.strip()[:12], flush=True)
        current = json.loads(docker("inspect", NAME).stdout)[0]
    values = dict(item.split("=", 1) for item in current["Config"].get("Env", []) if "=" in item)
    user = values.get("POSTGRES_USER", "postgres")
    database = values.get("POSTGRES_DB", user)
    print("Waiting for PostgreSQL...", flush=True)
    for _ in range(90):
        ready = docker("exec", NAME, "pg_isready", "-U", user, "-d", database, check=False)
        if ready.returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError("PostgreSQL did not become ready. Run: docker logs quizai-db")
    query = "SELECT 1 FROM pg_database WHERE datname='quizai_test'"
    exists = docker("exec", NAME, "psql", "-U", user, "-d", database, "-tAc", query).stdout.strip()
    if exists != "1":
        docker("exec", NAME, "createdb", "-U", user, "quizai_test")
    verified = docker("exec", NAME, "psql", "-U", user, "-d", "quizai_test",
                      "-tAc", "SELECT current_database()").stdout.strip()
    if verified != "quizai_test":
        raise RuntimeError("Test database verification failed")
    port = docker("port", NAME, "5432/tcp").stdout.strip()
    print("SUCCESS: PostgreSQL is running and quizai_test is ready.")
    print("Database address: " + port)
    print("Database user: " + user)
    print("Main database: " + database)
    print("Password remains in local .env.")
    print("Connect: docker exec -it quizai-db psql -U " + user + " -d " + database)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("STARTUP FAILED: " + str(error), file=sys.stderr)
        sys.exit(1)

"""Start local Keycloak. Operator password stays in ignored keycloak/.env."""
import secrets
import subprocess
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    try:
        check = subprocess.run(["docker", "info"], capture_output=True, check=False)
    except FileNotFoundError:
        raise SystemExit("Docker is not installed") from None
    if check.returncode:
        raise SystemExit("Docker API is unavailable. Start Docker Desktop and check its access permissions.")
    env = root / ".env"
    if not env.exists():
        env.write_text("KC_BOOTSTRAP_ADMIN_USERNAME=operator\nKC_BOOTSTRAP_ADMIN_PASSWORD="
                       + secrets.token_urlsafe(32) + "\n", encoding="utf-8")
    subprocess.run(["docker", "compose", "--env-file", str(env), "-f", str(root / "compose.yaml"),
                    "up", "-d"], check=True)
    print("Keycloak: http://localhost:8080 ; realm: delul")
    print("Local demo users: student/teacher/admin @demo.kz ; password: demo-pass-123")
    print("Operator password is stored only in keycloak/.env. Do not commit that file.")


if __name__ == "__main__":
    main()

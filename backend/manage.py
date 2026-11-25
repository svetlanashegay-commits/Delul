"""Local operator tool: python manage.py set-password EMAIL. Never prints passwords."""

import argparse
from getpass import getpass

from app.core.database import SessionLocal
from app.core.passwords import hash_password
from app.repositories import session_repository, user_repository
from app.repositories.unit_of_work import transaction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["set-password"])
    parser.add_argument("email")
    args = parser.parse_args()
    password = getpass("New password (at least 8 characters): ")
    if not 8 <= len(password) <= 128 or password != getpass("Repeat password: "):
        raise SystemExit("Password length or confirmation is invalid")
    with SessionLocal() as db, transaction(db):
        user = user_repository.find_by_email(db, args.email)
        if user is None:
            raise SystemExit("User not found; run seed or register the user first")
        user.password_hash = hash_password(password)
        user_repository.save(db, user)
        session_repository.revoke_user(db, user.id)
    print("Password updated; existing sessions revoked.")


if __name__ == "__main__":
    main()

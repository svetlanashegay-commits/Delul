"""Link an existing profile: python manage.py link-keycloak EMAIL SUBJECT."""

import argparse

from app.core.config import settings
from app.core.database import SessionLocal
from app.repositories import session_repository, user_repository
from app.repositories.unit_of_work import transaction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["link-keycloak"])
    parser.add_argument("email")
    parser.add_argument("subject", nargs="?")
    parser.add_argument("--issuer", default=settings.keycloak_issuer)
    args = parser.parse_args()
    if args.command == "link-keycloak":
        if not args.subject or len(args.subject) > 255:
            raise SystemExit("Provide the exact Keycloak subject ID")
        with SessionLocal() as db, transaction(db):
            user = user_repository.find_by_email(db, args.email)
            if user is None:
                raise SystemExit("Local user not found")
            linked = user_repository.find_by_keycloak(db, args.issuer, args.subject)
            if linked is not None and linked.id != user.id:
                raise SystemExit("This issuer/subject is linked to another local user")
            if user.keycloak_id and (
                user.keycloak_id != args.subject or user.keycloak_issuer != args.issuer
            ):
                raise SystemExit("User already has a different Keycloak identity")
            user.keycloak_id = args.subject
            user.keycloak_issuer = args.issuer
            user_repository.save(db, user)
            session_repository.revoke_user(db, user.id)
        print("Keycloak identity linked; local user ID and attempt history preserved.")
        return


if __name__ == "__main__":
    main()

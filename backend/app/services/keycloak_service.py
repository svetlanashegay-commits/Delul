from sqlalchemy.orm import Session

from app.repositories import user_repository as repository
from app.schemas.identity import Identity
from app.services.errors import ConflictError
from app.services.transactions import transaction


def resolve_user(db: Session, identity: Identity, group_name: str | None = None):
    with transaction(db):
        user = repository.find_by_keycloak(db, identity.issuer, identity.keycloak_id)
        group = group_name or identity.group_name or (user.group_name if user else None)
        if identity.role == "student" and not group:
            group = "Не указана"
        if user is None:
            # Matching an email alone must never grant access to an existing local account.
            if repository.find_by_email(db, identity.email):
                raise ConflictError(
                    "Local email exists; an operator must explicitly link its Keycloak subject"
                )
            return repository.create(
                db,
                {
                    "keycloak_id": identity.keycloak_id,
                    "keycloak_issuer": identity.issuer,
                    "email": identity.email,
                    "full_name": identity.full_name,
                    "role": identity.role,
                    "group_name": group,
                },
            )
        # A verified realm role is authoritative; a local profile cannot elevate it.
        user.role = identity.role
        user.full_name = identity.full_name
        user.group_name = group
        return repository.save(db, user)

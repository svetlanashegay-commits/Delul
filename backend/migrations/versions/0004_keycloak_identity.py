"""Bind local profiles to a verified issuer and subject, never to email alone."""

import sqlalchemy as sa
from alembic import op

revision = "0004_keycloak_identity"
down_revision = "0003_protected_attempts"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("keycloak_id", sa.String(255), nullable=True))
        batch.add_column(sa.Column("keycloak_issuer", sa.String(512), nullable=True))
        batch.create_unique_constraint(
            "uq_users_keycloak_identity", ["keycloak_issuer", "keycloak_id"]
        )
        batch.create_check_constraint(
            "ck_users_keycloak_identity",
            "(keycloak_id IS NULL AND keycloak_issuer IS NULL) OR "
            "(keycloak_id IS NOT NULL AND keycloak_issuer IS NOT NULL)",
        )


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_keycloak_identity", type_="check")
        batch.drop_constraint("uq_users_keycloak_identity", type_="unique")
        batch.drop_column("keycloak_id")
        batch.drop_column("keycloak_issuer")

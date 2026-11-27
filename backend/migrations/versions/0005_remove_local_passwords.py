"""Remove local password storage after Keycloak migration."""
import sqlalchemy as sa
from alembic import op

revision = "0005_remove_local_passwords"
down_revision = "0004_keycloak_identity"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_column("password_hash")

def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("password_hash", sa.String(), nullable=True))

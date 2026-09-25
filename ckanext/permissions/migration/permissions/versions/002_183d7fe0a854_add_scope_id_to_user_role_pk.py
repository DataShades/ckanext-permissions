"""Add scope_id to perm_user_role primary key.

Revision ID: 183d7fe0a854
Revises: a849104ccfdc
Create Date: 2026-09-25 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "183d7fe0a854"
down_revision = "a849104ccfdc"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE perm_user_role SET scope_id = '' WHERE scope_id IS NULL")
    op.alter_column("perm_user_role", "scope_id", existing_type=sa.String(), nullable=False, server_default="")

    op.drop_constraint("perm_user_role_pkey", "perm_user_role", type_="primary")
    op.create_primary_key("perm_user_role_pkey", "perm_user_role", ["user_id", "role_id", "scope", "scope_id"])


def downgrade():
    # The old key allows one row per (user_id, role_id, scope), so extra
    # organization assignments of the same role are dropped.
    op.execute(
        """
        DELETE FROM perm_user_role a
        USING perm_user_role b
        WHERE a.user_id = b.user_id
          AND a.role_id = b.role_id
          AND a.scope = b.scope
          AND a.scope_id > b.scope_id
        """
    )

    op.drop_constraint("perm_user_role_pkey", "perm_user_role", type_="primary")
    op.create_primary_key("perm_user_role_pkey", "perm_user_role", ["user_id", "role_id", "scope"])

    op.alter_column("perm_user_role", "scope_id", existing_type=sa.String(), nullable=True, server_default=None)
    op.execute("UPDATE perm_user_role SET scope_id = NULL WHERE scope_id = ''")

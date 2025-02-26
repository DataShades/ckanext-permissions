"""Init tables

Revision ID: a849104ccfdc
Revises:
Create Date: 2024-02-14 17:11:12.064281

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a849104ccfdc"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "perm_role",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
    )

    op.create_table(
        "perm_user_role",
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role_id",
            sa.String(),
            sa.ForeignKey("perm_role.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "perm_role_permission",
        sa.Column(
            "role_id",
            sa.String(),
            sa.ForeignKey("perm_role.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("permission", sa.String(), nullable=False, primary_key=True),
    )

    # Insert default roles
    op.execute(
        "INSERT INTO perm_role (id, label, description) VALUES "
        "('anonymous', 'Anonymous', 'Default role for anonymous users'), "
        "('user', 'User', 'Regular user that will be assigned automatically for "
        "all users on a portal'), "
        "('sysadmin', 'Sysadmin', 'Superuser that can do everything') "
    )


def downgrade():
    op.drop_table("perm_role_permission")
    op.drop_table("perm_user_role")
    op.drop_table("perm_role")

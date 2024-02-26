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
        "perm_permission_group",
        sa.Column("name", sa.Text, primary_key=True, unique=True),
        sa.Column("description", sa.Text, nullable=True),
    )

    op.create_table(
        "perm_permission",
        sa.Column("id", sa.Text, primary_key=True, unique=True),
        sa.Column("key", sa.Text, unique=True),
        sa.Column("label", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "group",
            sa.Text,
            sa.ForeignKey("perm_permission_group.name", ondelete="CASCADE"),
        ),
    )

    op.create_table(
        "perm_role",
        sa.Column("id", sa.Text, primary_key=True, unique=True),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("state", sa.Text, nullable=False),
        sa.Column(
            "permission",
            sa.Text,
            sa.ForeignKey("perm_permission.key", ondelete="CASCADE"),
        ),
    )


def downgrade():
    op.drop_table("perm_role")
    op.drop_table("perm_permission")
    op.drop_table("perm_permission_group")

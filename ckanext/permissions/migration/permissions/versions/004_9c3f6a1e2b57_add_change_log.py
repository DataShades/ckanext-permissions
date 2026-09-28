"""Add the change log table.

Revision ID: 9c3f6a1e2b57
Revises: 5b1e7c2d9f40
Create Date: 2026-09-28 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "9c3f6a1e2b57"
down_revision = "5b1e7c2d9f40"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "perm_change_log",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("role_id", sa.String(), nullable=False),
        sa.Column("permission", sa.String(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("data", JSONB(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_perm_change_log_timestamp", "perm_change_log", ["timestamp"])


def downgrade():
    op.drop_index("ix_perm_change_log_timestamp", "perm_change_log")
    op.drop_table("perm_change_log")

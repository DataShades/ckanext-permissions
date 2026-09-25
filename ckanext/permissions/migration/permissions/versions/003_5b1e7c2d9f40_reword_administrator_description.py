"""Reword the default administrator role description.

Revision ID: 5b1e7c2d9f40
Revises: 183d7fe0a854
Create Date: 2026-09-25 21:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5b1e7c2d9f40"
down_revision = "183d7fe0a854"
branch_labels = None
depends_on = None

OLD_DESCRIPTION = "Administrator that should have all permissions"
NEW_DESCRIPTION = "Role for portal administrators. It has no permissions until they are granted on the permissions page"


def _replace_description(old: str, new: str) -> None:
    op.execute(
        sa.text("UPDATE perm_role SET description = :new WHERE id = 'administrator' AND description = :old").bindparams(
            old=old, new=new
        )
    )


def upgrade():
    _replace_description(OLD_DESCRIPTION, NEW_DESCRIPTION)


def downgrade():
    _replace_description(NEW_DESCRIPTION, OLD_DESCRIPTION)

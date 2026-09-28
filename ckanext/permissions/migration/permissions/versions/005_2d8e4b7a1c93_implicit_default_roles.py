"""Create the default roles and drop the assignments of the implicit ones.

The anonymous and authenticated roles apply to users without being assigned.

Revision ID: 2d8e4b7a1c93
Revises: 9c3f6a1e2b57
Create Date: 2026-09-28 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2d8e4b7a1c93"
down_revision = "9c3f6a1e2b57"
branch_labels = None
depends_on = None

ANONYMOUS_DESCRIPTION = "Everyone, including visitors who aren't logged in"
AUTHENTICATED_DESCRIPTION = "Every logged-in user"

OLD_DESCRIPTIONS = {
    "anonymous": ("Default role for anonymous users", ANONYMOUS_DESCRIPTION),
    "authenticated": (
        "Regular user that will be assigned automatically for all users on a portal",
        AUTHENTICATED_DESCRIPTION,
    ),
}

DEFAULT_ROLES = [
    ("anonymous", "Anonymous", ANONYMOUS_DESCRIPTION),
    ("authenticated", "Authenticated", AUTHENTICATED_DESCRIPTION),
    (
        "administrator",
        "Administrator",
        "Role for portal administrators. It has no permissions until they are granted on the permissions page",
    ),
]


def upgrade():
    for role_id, label, description in DEFAULT_ROLES:
        op.execute(
            sa.text(
                "INSERT INTO perm_role (id, label, description) VALUES (:id, :label, :description) "
                "ON CONFLICT (id) DO NOTHING"
            ).bindparams(id=role_id, label=label, description=description)
        )

    for role_id, (old, new) in OLD_DESCRIPTIONS.items():
        _replace_description(role_id, old, new)

    op.execute("DELETE FROM perm_user_role WHERE role_id IN ('anonymous', 'authenticated')")


def downgrade():
    for role_id, (old, new) in OLD_DESCRIPTIONS.items():
        _replace_description(role_id, new, old)

    # The default roles stay, deleting them would cascade away their grants.
    # Revision 9c3f6a1e2b57 expects every active user to be assigned the authenticated role.
    op.execute(
        """
        INSERT INTO perm_user_role (user_id, role_id, scope, scope_id)
        SELECT id, 'authenticated', 'global', '' FROM "user" WHERE state = 'active'
        ON CONFLICT DO NOTHING
        """
    )


def _replace_description(role_id: str, old: str, new: str) -> None:
    op.execute(
        sa.text("UPDATE perm_role SET description = :new WHERE id = :id AND description = :old").bindparams(
            id=role_id, old=old, new=new
        )
    )

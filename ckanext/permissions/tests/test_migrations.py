from typing import cast

import pytest

from ckan import model

from ckanext.permissions import const
from ckanext.permissions import model as perm_model

BEFORE_IMPLICIT_ROLES = "9c3f6a1e2b57"
OLD_AUTHENTICATED_DESCRIPTION = "Regular user that will be assigned automatically for all users on a portal"


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestImplicitRolesMigration:
    def test_creates_default_roles(self, migrate_db_for):
        for role in const.Roles:
            cast(perm_model.Role, perm_model.Role.get(role.value)).delete()

        migrate_db_for("permissions", BEFORE_IMPLICIT_ROLES, forward=False)
        migrate_db_for("permissions")

        assert [role["id"] for role in perm_model.Role.all()] == [role.value for role in const.Roles]

    def test_drops_assignments_of_implicit_roles(self, migrate_db_for, organization):
        migrate_db_for("permissions", BEFORE_IMPLICIT_ROLES, forward=False)

        user = model.User(name="active-user", email="active@example.com")
        model.Session.add(user)
        model.Session.commit()

        perm_model.UserRole.create(user.id, const.Roles.Anonymous.value)
        perm_model.UserRole.create(
            user.id, const.Roles.Authenticated.value, const.SCOPE_ORGANIZATION, organization["id"]
        )
        perm_model.UserRole.create(user.id, const.Roles.Administrator.value)

        migrate_db_for("permissions")

        assert [user_role.role_id for user_role in perm_model.UserRole.get(user.id)] == [
            const.Roles.Administrator.value
        ]
        assert not perm_model.UserRole.get(user.id, const.SCOPE_ORGANIZATION)

    def test_downgrade_gives_authenticated_role_back_to_active_users(self, migrate_db_for):
        active = model.User(name="active-user", email="active@example.com")
        deleted = model.User(name="deleted-user", email="deleted@example.com", state=model.State.DELETED)
        model.Session.add_all([active, deleted])
        model.Session.commit()

        migrate_db_for("permissions", BEFORE_IMPLICIT_ROLES, forward=False)

        assert [user_role.role_id for user_role in perm_model.UserRole.get(active.id)] == [
            const.Roles.Authenticated.value
        ]
        assert not perm_model.UserRole.get(deleted.id)

    def test_rewords_default_description(self, migrate_db_for):
        role = cast(perm_model.Role, perm_model.Role.get(const.Roles.Authenticated.value))
        role.update(OLD_AUTHENTICATED_DESCRIPTION)

        migrate_db_for("permissions", BEFORE_IMPLICIT_ROLES, forward=False)
        migrate_db_for("permissions")
        model.Session.expire_all()

        assert role.description == "Every logged-in user"

    def test_keeps_edited_roles(self, migrate_db_for):
        role = perm_model.Role.get(const.Roles.Authenticated.value)
        assert role
        role.update("Edited description", "Members")

        migrate_db_for("permissions", BEFORE_IMPLICIT_ROLES, forward=False)
        migrate_db_for("permissions")
        model.Session.expire_all()

        role = perm_model.Role.get(const.Roles.Authenticated.value)
        assert role
        assert (role.label, role.description) == ("Members", "Edited description")

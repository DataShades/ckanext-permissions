import pytest

from ckan.tests.helpers import call_action

from ckanext.permissions import const, helpers, model
from ckanext.permissions_manager.helpers import permission_get_registered_roles_options


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestGetRegisteredRoles:
    def test_get_default_roles(self):
        result = helpers.get_registered_roles()

        assert len(result) == 3

        assert result[const.Roles.Anonymous.value]
        assert result[const.Roles.Authenticated.value]
        assert result[const.Roles.Administrator.value]

    def test_with_custom_roles(self, test_role: dict[str, str]):
        result = helpers.get_registered_roles()

        assert len(result) == 4
        assert result[test_role["id"]] == test_role["label"]

    def test_order(self):
        call_action("permission_role_create", id="aaa", label="Zeta", description="xxx")
        call_action("permission_role_create", id="zzz", label="Alpha", description="xxx")

        assert list(helpers.get_registered_roles()) == [
            const.Roles.Anonymous.value,
            const.Roles.Authenticated.value,
            const.Roles.Administrator.value,
            "zzz",
            "aaa",
        ]


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestGetRolePermissions:
    def test_no_permission(self, test_role: dict[str, str]):
        assert not helpers.get_role_permissions(test_role["id"], "read_any_dataset")

    def test_with_permission(self, test_role: dict[str, str]):
        call_action(
            "permissions_update",
            permissions={"read_any_dataset": {test_role["id"]: True}},
        )

        assert helpers.get_role_permissions(test_role["id"], "read_any_dataset")


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestGetUserRoles:
    def test_only_default_roles(self, user: dict[str, str]):
        assert helpers.get_user_roles(user["id"]) == ["authenticated"]

    def test_add_new_role(self, user: dict[str, str], test_role: dict[str, str]):
        model.UserRole.create(user["id"], test_role["id"])
        result = helpers.get_user_roles(user["id"])
        assert "authenticated" in result
        assert test_role["id"] in result

    def test_remove_role(self, user: dict[str, str], test_role: dict[str, str]):
        model.UserRole.create(user["id"], test_role["id"])
        result = helpers.get_user_roles(user["id"])
        assert "authenticated" in result
        assert test_role["id"] in result

        model.UserRole.delete(user["id"], test_role["id"])
        assert helpers.get_user_roles(user["id"]) == ["authenticated"]


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestIsDefaultRole:
    def test_is_default_role(self):
        assert helpers.is_default_role(const.Roles.Authenticated.value)

    def test_is_not_default_role(self, test_role: dict[str, str]):
        assert not helpers.is_default_role("test_role")


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRegisteredRolesOptions:
    def test_only_anonymous_is_excluded(self, role_factory):
        role_factory(id="anon", label="Anon")

        values = [option["value"] for option in permission_get_registered_roles_options()]

        assert const.Roles.Anonymous.value not in values
        assert "anon" in values

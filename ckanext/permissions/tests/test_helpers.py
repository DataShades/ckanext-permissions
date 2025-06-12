import pytest

from ckan.tests.helpers import call_action

from ckanext.permissions import const, helpers, model


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestGetRegisteredRoles:
    def test_get_default_roles(self):
        result = helpers.get_registered_roles()

        assert len(result) == 3

        assert result[const.Roles.Anonymous.value]
        assert result[const.Roles.User.value]
        assert result[const.Roles.Sysadmin.value]

    def test_with_custom_roles(self, test_role: dict[str, str]):
        result = helpers.get_registered_roles()

        assert len(result) == 4
        assert result[test_role["id"]] == test_role["label"]


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
        assert helpers.get_user_roles(user["id"]) == ["user"]

    def test_add_new_role(self, user: dict[str, str], test_role: dict[str, str]):
        model.UserRole.create(user["id"], test_role["id"])
        result = helpers.get_user_roles(user["id"])
        assert "user" in result
        assert test_role["id"] in result

    def test_remove_role(self, user: dict[str, str], test_role: dict[str, str]):
        model.UserRole.create(user["id"], test_role["id"])
        result = helpers.get_user_roles(user["id"])
        assert "user" in result
        assert test_role["id"] in result

        model.UserRole.delete(user["id"], test_role["id"])
        assert helpers.get_user_roles(user["id"]) == ["user"]


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestIsDefaultRole:
    def test_is_default_role(self):
        assert helpers.is_default_role(const.Roles.User.value)

    def test_is_not_default_role(self, test_role: dict[str, str]):
        assert not helpers.is_default_role("test_role")

import pytest

import ckan.plugins.toolkit as tk
from ckan.tests.helpers import call_action

from ckanext.permissions import model as perm_model


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPermissionsUpdate:
    def test_permissions_update(self):
        result = call_action(
            "permissions_update",
            permissions={
                "perm_1": {"anonymous": False, "user": True, "sysadmin": True},
                "perm_2": {"anonymous": False, "user": True, "sysadmin": True},
            },
        )

        assert not result["missing_permissions"]
        assert result["updated_permissions"] == {
            "perm_1": {"user": True, "sysadmin": True},
            "perm_2": {"user": True, "sysadmin": True},
        }

        assert not perm_model.RolePermission.get("anonymous", "perm_1")
        assert perm_model.RolePermission.get("user", "perm_1")
        assert perm_model.RolePermission.get("sysadmin", "perm_1")

        result = call_action(
            "permissions_update",
            permissions={"perm_1": {"anonymous": True}},
        )

        assert perm_model.RolePermission.get("anonymous", "perm_1")

    def test_permissions_update_unregistered_permission_key(self):
        result = call_action("permissions_update", permissions={"xxx": {}})

        assert result["missing_permissions"] == ["xxx"]
        assert not result["updated_permissions"]

    def test_not_string_permission_key(self):
        with pytest.raises(tk.ValidationError, match="Invalid permission key"):
            call_action("permissions_update", permissions={1: {}})

    def test_not_dict_roles_mapping(self):
        with pytest.raises(tk.ValidationError, match="Invalid permission mapping"):
            call_action("permissions_update", permissions={"perm_1": 1})

    def test_not_bool_permission_value(self):
        with pytest.raises(tk.ValidationError, match="Invalid permission value"):
            call_action(
                "permissions_update",
                permissions={"perm_1": {"anonymous": "xxx", "user": "yyy"}},
            )

    def test_role_id_not_exists(self):
        with pytest.raises(tk.ValidationError, match="Role xxx doesn't exists"):
            call_action("permissions_update", permissions={"perm_1": {"xxx": True}})

import pytest

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.tests.helpers import call_action

from ckanext.permissions import model as perm_model


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPermissionsUpdate:
    def test_permissions_update(self):
        result = call_action(
            "permissions_update",
            permissions={
                "perm_1": {
                    "anonymous": False,
                    "authenticated": True,
                    "administrator": True,
                },
                "perm_2": {
                    "anonymous": False,
                    "authenticated": True,
                    "administrator": True,
                },
            },
        )

        assert not result["missing_permissions"]
        assert result["updated_permissions"] == {
            "perm_1": {"authenticated": True, "administrator": True},
            "perm_2": {"authenticated": True, "administrator": True},
        }

        assert not perm_model.RolePermission.get("anonymous", "perm_1")
        assert perm_model.RolePermission.get("authenticated", "perm_1")
        assert perm_model.RolePermission.get("administrator", "perm_1")

        result = call_action(
            "permissions_update",
            permissions={"perm_1": {"anonymous": True}},
        )

        assert perm_model.RolePermission.get("anonymous", "perm_1")

    def test_permissions_grant_and_revoke_are_committed(self):
        call_action("permissions_update", permissions={"perm_1": {"anonymous": True}})

        call_action(
            "permissions_update",
            permissions={"perm_1": {"anonymous": False, "authenticated": True}},
        )
        model.Session.rollback()

        assert not perm_model.RolePermission.get("anonymous", "perm_1")
        assert perm_model.RolePermission.get("authenticated", "perm_1")

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
                permissions={"perm_1": {"anonymous": "xxx", "authenticated": "yyy"}},
            )

    def test_role_id_not_exists(self):
        with pytest.raises(tk.ValidationError, match="Role xxx doesn't exists"):
            call_action("permissions_update", permissions={"perm_1": {"xxx": True}})

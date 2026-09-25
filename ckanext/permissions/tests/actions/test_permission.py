import logging

import pytest

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.tests.helpers import call_action

from ckanext.permissions import model as perm_model
from ckanext.permissions import utils


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

    def test_permission_changes_are_logged(self, caplog):
        call_action("permissions_update", permissions={"perm_1": {"anonymous": True}})

        with caplog.at_level(logging.INFO, logger="ckanext.permissions.logic.action"):
            call_action(
                "permissions_update",
                permissions={"perm_1": {"anonymous": False, "authenticated": True}},
            )

        assert "Permission revoked: permission=perm_1 role=anonymous" in caplog.text
        assert "Permission granted: permission=perm_1 role=authenticated" in caplog.text

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


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPermissionDependencies:
    @pytest.mark.parametrize(
        ("permission", "dependency"),
        [
            ("update_any_dataset", "read_any_dataset"),
            ("delete_any_dataset", "read_any_dataset"),
            ("delete_any_resource", "update_any_dataset"),
        ],
    )
    def test_grant_without_dependency_is_rejected(self, permission, dependency):
        with pytest.raises(tk.ValidationError, match=f"also needs: {dependency}"):
            call_action("permissions_update", permissions={permission: {"authenticated": True}})

        assert not perm_model.RolePermission.get("authenticated", permission)

    def test_grant_with_dependency_in_same_request(self):
        call_action(
            "permissions_update",
            permissions={
                "read_any_dataset": {"authenticated": True},
                "update_any_dataset": {"authenticated": True},
            },
        )

        assert perm_model.RolePermission.get("authenticated", "update_any_dataset")

    def test_revoke_dependency_of_granted_permission_is_rejected(self):
        call_action(
            "permissions_update",
            permissions={
                "read_any_dataset": {"authenticated": True},
                "update_any_dataset": {"authenticated": True},
            },
        )

        with pytest.raises(tk.ValidationError, match="depend on it: update_any_dataset"):
            call_action("permissions_update", permissions={"read_any_dataset": {"authenticated": False}})

        assert perm_model.RolePermission.get("authenticated", "read_any_dataset")

    def test_revoke_dependency_with_dependents_in_same_request(self):
        permissions = {"read_any_dataset": {"authenticated": True}, "update_any_dataset": {"authenticated": True}}
        call_action("permissions_update", permissions=permissions)

        call_action(
            "permissions_update",
            permissions={
                "read_any_dataset": {"authenticated": False},
                "update_any_dataset": {"authenticated": False},
            },
        )

        assert not perm_model.RolePermission.get("authenticated", "read_any_dataset")
        assert not perm_model.RolePermission.get("authenticated", "update_any_dataset")

    def test_dependency_is_per_role(self):
        call_action("permissions_update", permissions={"read_any_dataset": {"administrator": True}})

        with pytest.raises(tk.ValidationError, match="Role authenticated also needs"):
            call_action("permissions_update", permissions={"update_any_dataset": {"authenticated": True}})


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestAnonymousRestriction:
    def test_grant_to_anonymous_is_rejected(self):
        with pytest.raises(tk.ValidationError, match="can't be given to the anonymous role"):
            call_action(
                "permissions_update",
                permissions={
                    "read_any_dataset": {"anonymous": True},
                    "update_any_dataset": {"anonymous": True},
                },
            )

        assert not perm_model.RolePermission.get("anonymous", "read_any_dataset")
        assert not perm_model.RolePermission.get("anonymous", "update_any_dataset")

    def test_revoke_from_anonymous_is_allowed(self):
        perm_model.RolePermission.create("anonymous", "update_any_dataset")

        call_action("permissions_update", permissions={"update_any_dataset": {"anonymous": False}})

        assert not perm_model.RolePermission.get("anonymous", "update_any_dataset")

    def test_existing_grant_is_ignored(self):
        perm_model.RolePermission.create("anonymous", "update_any_dataset")

        assert not utils.check_permission("update_any_dataset", model.AnonymousUser())

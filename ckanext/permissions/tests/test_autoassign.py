import pytest

import ckan.plugins.toolkit as tk
from ckan.tests.helpers import call_action

import ckanext.permissions.model as perm_model


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRoleAutoassignment:
    def test_assign_user_role_on_create(self, user):
        """Test if a role is assigned to a user when it's created"""
        roles = tk.h.get_user_roles(user["id"])
        assert roles == ["user"]

    def test_user_roles_deleted_with_role(self, user, test_role):
        """Test if user roles are deleted when the role is deleted"""
        perm_model.UserRole.create(user["id"], test_role["id"])

        result = tk.h.get_user_roles(user["id"])
        assert "user" in result
        assert "creator" in result

        call_action("permission_role_delete", id=test_role["id"])

        assert tk.h.get_user_roles(user["id"]) == ["user"]

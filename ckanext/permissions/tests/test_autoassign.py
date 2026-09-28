import pytest

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.tests.helpers import call_action

import ckanext.permissions.model as perm_model


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRoleAssignments:
    def test_new_user_gets_no_role_rows(self, user):
        assert tk.h.get_user_roles(user["id"]) == []

    def test_user_roles_deleted_with_role(self, user, test_role):
        perm_model.UserRole.create(user["id"], test_role["id"])

        call_action("permission_role_delete", id=test_role["id"])

        assert tk.h.get_user_roles(user["id"]) == []

    def test_role_kept_when_user_role_deleted(self, user, test_role):
        user_role = perm_model.UserRole.create(user["id"], test_role["id"])

        model.Session.delete(user_role)
        model.Session.commit()

        assert perm_model.Role.get(test_role["id"]) is not None

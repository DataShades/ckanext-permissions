import pytest

import ckan.plugins.toolkit as tk

from ckanext.permissions import const
from ckanext.permissions import model as perm_model


@pytest.mark.ckan_config("ckan.plugins", "permissions permissions_manager")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestInvalidInput:
    @pytest.mark.parametrize("limit", ["abc", "0", "100000"])
    def test_user_roles_limit(self, app, sysadmin, limit):
        url = tk.h.url_for("perm_manager.user_roles_list", limit=limit)

        app.get(url, headers={"Authorization": sysadmin["token"]}, status=200)

    def test_permissions_form_key_with_extra_pipe(self, app, sysadmin):
        url = tk.h.url_for("perm_manager.permission_list")

        app.post(
            url,
            data={"perm_1|anonymous|extra": "set"},
            headers={"Authorization": sysadmin["token"]},
            follow_redirects=False,
            status=302,
        )

    def test_add_role_missing_fields(self, app, sysadmin):
        url = tk.h.url_for("perm_manager.role_add")

        app.post(url, data={}, headers={"Authorization": sysadmin["token"]}, status=200)

    def test_delete_role_missing_id(self, app, sysadmin):
        url = tk.h.url_for("perm_manager.role_delete")

        app.post(url, data={}, headers={"Authorization": sysadmin["token"]}, follow_redirects=False, status=302)

    def test_edit_role_missing_description(self, app, sysadmin, test_role):
        url = tk.h.url_for("perm_manager.role_edit", role_id=test_role["id"])

        app.post(url, data={}, headers={"Authorization": sysadmin["token"]}, status=200)

    @pytest.mark.parametrize("method", ["get", "post"])
    def test_edit_unknown_role(self, app, sysadmin, method):
        url = tk.h.url_for("perm_manager.role_edit", role_id="missing")

        getattr(app, method)(url, headers={"Authorization": sysadmin["token"]}, status=404)

    def test_org_user_roles_unknown_org(self, app, sysadmin, user):
        url = tk.h.url_for("perm_manager.organization_edit_user_role", org_id="missing", user_id=user["id"])

        app.post(url, data={"roles": ["administrator"]}, headers={"Authorization": sysadmin["token"]}, status=404)

    def test_org_user_roles_stored_by_org_id(self, app, sysadmin, user, organization):
        url = tk.h.url_for("perm_manager.organization_edit_user_role", org_id=organization["name"], user_id=user["id"])

        app.post(
            url,
            data={"roles": [const.Roles.Administrator.value]},
            headers={"Authorization": sysadmin["token"]},
            follow_redirects=False,
            status=302,
        )

        user_roles = perm_model.UserRole.get(user["id"], const.SCOPE_ORGANIZATION, organization["id"])
        assert [role.role_id for role in user_roles] == [const.Roles.Administrator.value]

import logging

import pytest

import ckan.plugins.toolkit as tk

from ckanext.permissions import const, utils
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

    def test_org_user_roles_same_role_in_second_org(self, app, sysadmin, user, organization_factory):
        admin = const.Roles.Administrator.value
        orgs = [organization_factory(), organization_factory()]

        for org in orgs:
            url = tk.h.url_for("perm_manager.organization_edit_user_role", org_id=org["id"], user_id=user["id"])
            app.post(
                url,
                data={"roles": [admin]},
                headers={"Authorization": sysadmin["token"]},
                follow_redirects=False,
                status=302,
            )

        for org in orgs:
            user_roles = perm_model.UserRole.get(user["id"], const.SCOPE_ORGANIZATION, org["id"])
            assert [role.role_id for role in user_roles] == [admin]


@pytest.mark.ckan_config("ckan.plugins", "permissions permissions_manager")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestAuditLog:
    def test_user_roles_update_is_logged(self, app, sysadmin, user, caplog):
        url = tk.h.url_for("perm_manager.edit_user_role", user_id=user["id"])

        with caplog.at_level(logging.INFO, logger="ckanext.permissions_manager.views"):
            app.post(
                url,
                data={"roles": [const.Roles.Administrator.value]},
                headers={"Authorization": sysadmin["token"]},
                follow_redirects=False,
                status=302,
            )

        assert (
            f"User roles updated: user={user['name']} scope=global scope_id=None "
            f"added=['administrator'] removed=['authenticated'] actor={sysadmin['name']}"
        ) in caplog.text


@pytest.mark.ckan_config("ckan.plugins", "permissions permissions_manager")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestUserRolesList:
    def test_filter_by_role(self, app, sysadmin, user_factory):
        admin = user_factory(fullname="Alice Admin")
        user_factory(fullname="Bob Plain")
        utils.assign_role_to_user(admin["id"], const.Roles.Administrator.value)

        url = tk.h.url_for("perm_manager.user_roles_list", role=const.Roles.Administrator.value)
        body = app.get(url, headers={"Authorization": sysadmin["token"]}, status=200).body

        assert "Alice Admin" in body
        assert "Bob Plain" not in body

    def test_filter_by_name(self, app, sysadmin, user_factory):
        user_factory(fullname="Alice Admin")
        user_factory(fullname="Bob Plain")

        url = tk.h.url_for("perm_manager.user_roles_list", q="bob")
        body = app.get(url, headers={"Authorization": sysadmin["token"]}, status=200).body

        assert "Bob Plain" in body
        assert "Alice Admin" not in body

    def test_page_past_end_shows_last_page(self, app, sysadmin, user_factory):
        user_factory(fullname="Zzzz Last")

        url = tk.h.url_for("perm_manager.user_roles_list", limit=1, page=999)
        body = app.get(url, headers={"Authorization": sysadmin["token"]}, status=200).body

        assert "Zzzz Last" in body

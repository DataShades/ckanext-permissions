import logging
import re

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

    def test_org_list_shows_members_and_scoped_roles_by_default(
        self, app, sysadmin, user_factory, organization_factory
    ):
        member = user_factory(fullname="Mia Member")
        scoped = user_factory(fullname="Sam Scoped")
        user_factory(fullname="Otto Outsider")
        org = organization_factory(users=[{"name": member["name"], "capacity": "member"}])
        utils.assign_role_to_user(scoped["id"], const.Roles.Administrator.value, const.SCOPE_ORGANIZATION, org["id"])
        headers = {"Authorization": sysadmin["token"]}

        body = app.get(
            tk.h.url_for("perm_manager.organization_user_roles_list", org_id=org["id"]), headers=headers
        ).body

        assert "Mia Member" in body
        assert "Sam Scoped" in body
        assert "Otto Outsider" not in body

        body = app.get(
            tk.h.url_for("perm_manager.organization_user_roles_list", org_id=org["id"], all=1), headers=headers
        ).body

        assert "Otto Outsider" in body

    def test_no_match_shows_empty_state(self, app, sysadmin):
        url = tk.h.url_for("perm_manager.user_roles_list", q="nobody-has-this-name")
        body = app.get(url, headers={"Authorization": sysadmin["token"]}, status=200).body

        assert "No users match your filters." in body
        assert "Showing" not in body

    def test_shows_result_count(self, app, sysadmin, user_factory):
        user_factory(fullname="Counted User")

        url = tk.h.url_for("perm_manager.user_roles_list", q="counted user")
        body = app.get(url, headers={"Authorization": sysadmin["token"]}, status=200).body

        assert "Showing 1–1 of 1" in body

    def test_role_badges_show_labels(self, app, sysadmin, user, test_role):
        utils.assign_role_to_user(user["id"], test_role["id"])

        url = tk.h.url_for("perm_manager.user_roles_list", role=test_role["id"])
        body = app.get(url, headers={"Authorization": sysadmin["token"]}, status=200).body

        assert f'<span class="badge bg-success">{test_role["label"]}</span>' in body


@pytest.mark.ckan_config("ckan.plugins", "permissions permissions_manager")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPermissionMatrix:
    def test_blocked_cell_has_no_toggle(self, app, sysadmin):
        body = app.get(
            tk.h.url_for("perm_manager.permission_list"), headers={"Authorization": sysadmin["token"]}, status=200
        ).body

        assert "Not allowed" in body
        assert 'id="anonymous-update_any_dataset"' not in body
        assert 'name="update_any_dataset|anonymous"' in body

    def test_rows_are_searchable_by_key(self, app, sysadmin):
        body = app.get(
            tk.h.url_for("perm_manager.permission_list"), headers={"Authorization": sysadmin["token"]}, status=200
        ).body

        assert re.search(r'data-search="[^"]*\bupdate_any_dataset\b', body)


PAGES = [
    ("perm_manager.permission_list", {}),
    ("perm_manager.role_list", {}),
    ("perm_manager.role_add", {}),
    ("perm_manager.role_edit", {"role_id": "{role}"}),
    ("perm_manager.user_roles_list", {}),
    ("perm_manager.edit_user_role", {"user_id": "{user}"}),
    ("perm_manager.organization_user_roles_list", {"org_id": "{org}"}),
    ("perm_manager.organization_edit_user_role", {"org_id": "{org}", "user_id": "{user}"}),
]

FORM_PAGES = [
    "perm_manager.permission_list",
    "perm_manager.role_list",
    "perm_manager.role_add",
    "perm_manager.role_edit",
    "perm_manager.edit_user_role",
    "perm_manager.organization_edit_user_role",
]


@pytest.fixture
def page_url(test_role, user, organization):
    def build(endpoint: str) -> str:
        kwargs = dict(next(kwargs for name, kwargs in PAGES if name == endpoint))
        values = {"role": test_role["id"], "user": user["id"], "org": organization["id"]}

        return tk.h.url_for(endpoint, **{key: value.format(**values) for key, value in kwargs.items()})

    return build


@pytest.mark.ckan_config("ckan.plugins", "permissions permissions_manager")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSysadminGate:
    @pytest.mark.parametrize("endpoint", [name for name, _ in PAGES])
    def test_sysadmin_allowed(self, app, sysadmin, page_url, endpoint):
        app.get(page_url(endpoint), headers={"Authorization": sysadmin["token"]}, status=200)

    @pytest.mark.parametrize("endpoint", [name for name, _ in PAGES])
    def test_regular_user_forbidden(self, app, user_factory, page_url, endpoint):
        other_user = user_factory()

        app.get(page_url(endpoint), headers={"Authorization": other_user["token"]}, status=403)

    @pytest.mark.parametrize("endpoint", [name for name, _ in PAGES])
    def test_anonymous_forbidden(self, app, page_url, endpoint):
        app.get(page_url(endpoint), status=403)

    @pytest.mark.parametrize("endpoint", FORM_PAGES)
    def test_forms_include_csrf_field(self, app, sysadmin, page_url, endpoint):
        body = app.get(page_url(endpoint), headers={"Authorization": sysadmin["token"]}, status=200).body

        assert f'name="{tk.config["WTF_CSRF_FIELD_NAME"]}"' in body


@pytest.mark.ckan_config("ckan.plugins", "permissions permissions_manager")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestForms:
    def _post(self, app, sysadmin, url, data):
        app.post(url, data=data, headers={"Authorization": sysadmin["token"]}, follow_redirects=False, status=302)

    def test_update_permissions(self, app, sysadmin):
        self._post(app, sysadmin, tk.h.url_for("perm_manager.permission_list"), {"perm_1|anonymous": "set"})

        assert perm_model.RolePermission.get(const.Roles.Anonymous.value, "perm_1")

    def test_add_role(self, app, sysadmin):
        data = {"id": "editor", "label": "Editor", "description": "Editor role"}

        self._post(app, sysadmin, tk.h.url_for("perm_manager.role_add"), data)

        assert perm_model.Role.get("editor")

    def test_edit_role(self, app, sysadmin, test_role):
        url = tk.h.url_for("perm_manager.role_edit", role_id=test_role["id"])

        self._post(app, sysadmin, url, {"description": "Updated"})

        role = perm_model.Role.get(test_role["id"])
        assert role
        assert str(role.description) == "Updated"

    def test_add_role_form_validates_id_in_browser(self, app, sysadmin):
        body = app.get(
            tk.h.url_for("perm_manager.role_add"), headers={"Authorization": sysadmin["token"]}, status=200
        ).body

        assert f'pattern="{const.ROLE_ID_PATTERN}"' in body
        assert f'maxlength="{const.ROLE_ID_MAX_LENGTH}"' in body

    def test_edit_role_label(self, app, sysadmin, test_role):
        url = tk.h.url_for("perm_manager.role_edit", role_id=test_role["id"])

        self._post(app, sysadmin, url, {"label": "Renamed", "description": "Updated"})

        role = perm_model.Role.get(test_role["id"])
        assert role
        assert str(role.label) == "Renamed"

    def test_delete_role(self, app, sysadmin, test_role):
        self._post(app, sysadmin, tk.h.url_for("perm_manager.role_delete"), {"id": test_role["id"]})

        assert perm_model.Role.get(test_role["id"]) is None

    def test_delete_role_asks_for_confirmation(self, app, sysadmin, user, test_role):
        utils.assign_role_to_user(user["id"], test_role["id"])
        perm_model.RolePermission.create(test_role["id"], "read_any_dataset")

        body = app.get(
            tk.h.url_for("perm_manager.role_list"), headers={"Authorization": sysadmin["token"]}, status=200
        ).body

        assert 'data-module="confirm-action"' in body
        assert f'<input type="hidden" name="id" value="{test_role["id"]}">' in body
        assert "It is assigned to 1 user and grants 1 permission." in body

    def test_edit_user_roles(self, app, sysadmin, user):
        url = tk.h.url_for("perm_manager.edit_user_role", user_id=user["id"])
        roles = [const.Roles.Administrator.value, const.Roles.Authenticated.value]

        self._post(app, sysadmin, url, {"roles": roles})

        assert sorted(tk.h.get_user_roles(user["id"])) == sorted(roles)

    def test_permissions_page_shows_dependencies(self, app, sysadmin):
        body = app.get(
            tk.h.url_for("perm_manager.permission_list"), headers={"Authorization": sysadmin["token"]}, status=200
        ).body

        assert "Requires:" in body
        assert 'data-permission="update_any_dataset"' in body
        assert 'data-depends-on="read_any_dataset"' in body


@pytest.mark.ckan_config("ckan.plugins", "permissions permissions_manager")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestNavigation:
    def test_styles_only_on_manager_pages(self, app, sysadmin):
        headers = {"Authorization": sysadmin["token"]}

        assert "permission-manager.css" not in app.get(tk.h.url_for("home.index"), headers=headers).body
        assert "permission-manager.css" in app.get(tk.h.url_for("perm_manager.role_list"), headers=headers).body

    def test_header_has_single_permissions_link(self, app, sysadmin):
        body = app.get(tk.h.url_for("home.index"), headers={"Authorization": sysadmin["token"]}, status=200).body

        assert f'href="{tk.h.url_for("perm_manager.permission_list")}"' in body
        assert "permissions-dropdown" not in body

    @pytest.mark.parametrize(
        ("endpoint", "active_tab"),
        [
            ("perm_manager.permission_list", "perm_manager.permission_list"),
            ("perm_manager.role_list", "perm_manager.role_list"),
            ("perm_manager.role_add", "perm_manager.role_list"),
            ("perm_manager.role_edit", "perm_manager.role_list"),
            ("perm_manager.user_roles_list", "perm_manager.user_roles_list"),
            ("perm_manager.edit_user_role", "perm_manager.user_roles_list"),
        ],
    )
    def test_active_tab(self, app, sysadmin, page_url, endpoint, active_tab):
        body = app.get(page_url(endpoint), headers={"Authorization": sysadmin["token"]}, status=200).body

        tabs = body.split('<ul class="nav nav-tabs">', 1)[1].split("</ul>", 1)[0]
        active = re.findall(r'<li class="active">\s*<a href="([^"]+)"', tabs)

        assert active == [tk.h.url_for(active_tab)]

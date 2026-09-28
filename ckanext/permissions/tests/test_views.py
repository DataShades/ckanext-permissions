import html
import json
import re

import pytest

import ckan.plugins.toolkit as tk

from ckanext.permissions import const, utils
from ckanext.permissions import model as perm_model


@pytest.mark.ckan_config("ckan.plugins", "permissions permissions_manager tables")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestInvalidInput:
    def test_permissions_form_key_with_extra_pipe(self, app, sysadmin):
        url = tk.h.url_for("perm_manager.permission_list")

        app.post(
            url,
            data={"perm_1|anonymous|extra": "set"},
            headers={"Authorization": sysadmin["token"]},
            status=200,
        )

    def test_add_role_missing_fields(self, app, sysadmin):
        url = tk.h.url_for("perm_manager.role_add")

        app.post(url, data={}, headers={"Authorization": sysadmin["token"]}, status=200)

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

    def test_user_roles_unknown_role_shows_form_error(self, app, sysadmin, user):
        url = tk.h.url_for("perm_manager.edit_user_role", user_id=user["id"])

        body = app.post(url, data={"roles": ["missing"]}, headers={"Authorization": sysadmin["token"]}, status=200).body

        assert 'name="roles"' in body
        assert f'href="{tk.h.url_for("perm_manager.user_roles_list")}"' in body

    @pytest.mark.parametrize("role", sorted(const.IMPLICIT_ROLES))
    def test_implicit_role_cant_be_assigned(self, app, sysadmin, user, role):
        url = tk.h.url_for("perm_manager.edit_user_role", user_id=user["id"])

        body = app.post(url, data={"roles": [role]}, headers={"Authorization": sysadmin["token"]}, status=200).body

        assert "applies to users automatically" in body
        assert not tk.h.get_user_roles(user["id"])

    def test_implicit_roles_arent_offered(self, app, sysadmin, user):
        url = tk.h.url_for("perm_manager.edit_user_role", user_id=user["id"])

        body = app.get(url, headers={"Authorization": sysadmin["token"]}, status=200).body

        assert f'<option value="{const.Roles.Administrator.value}"' in body
        for role in const.IMPLICIT_ROLES:
            assert f'<option value="{role}"' not in body

    def test_org_user_roles_unknown_role_shows_org_form(self, app, sysadmin, user, organization):
        url = tk.h.url_for("perm_manager.organization_edit_user_role", org_id=organization["id"], user_id=user["id"])

        body = app.post(url, data={"roles": ["missing"]}, headers={"Authorization": sysadmin["token"]}, status=200).body

        assert 'name="roles"' in body
        org_list_url = tk.h.url_for("perm_manager.organization_user_roles_list", org_id=organization["id"])
        assert f'href="{org_list_url}"' in body

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


XHR = {"X-Requested-With": "XMLHttpRequest"}


def _table_rows(app, sysadmin, url, filters=None):
    params = {"filters": json.dumps(filters)} if filters else None
    resp = app.get(url, query_string=params, headers={"Authorization": sysadmin["token"], **XHR}, status=200)

    return {row["id"]: row for row in resp.json["data"]}


def _row_action(app, sysadmin, url, action, row):
    resp = app.post(
        url,
        data={"row_action": action, "row": json.dumps(row)},
        headers={"Authorization": sysadmin["token"]},
        status=200,
    )

    return resp.json


def _like(field, value):
    return [{"field": field, "operator": "like", "value": value}]


@pytest.mark.ckan_config("ckan.plugins", "permissions permissions_manager tables")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestUserRolesList:
    def test_filter_by_role(self, app, sysadmin, user_factory):
        admin = user_factory(fullname="Alice Admin")
        plain = user_factory(fullname="Bob Plain")
        utils.assign_role_to_user(admin["id"], const.Roles.Administrator.value)

        url = tk.h.url_for("perm_manager.user_roles_list")
        rows = _table_rows(app, sysadmin, url, _like("roles", "Administrator"))

        assert admin["id"] in rows
        assert plain["id"] not in rows

    def test_filter_by_name(self, app, sysadmin, user_factory):
        alice = user_factory(fullname="Alice Admin")
        bob = user_factory(fullname="Bob Plain")

        url = tk.h.url_for("perm_manager.user_roles_list")
        rows = _table_rows(app, sysadmin, url, _like("display_name", "bob"))

        assert bob["id"] in rows
        assert alice["id"] not in rows

    def test_org_list_shows_members_and_scoped_roles_by_default(
        self, app, sysadmin, user_factory, organization_factory
    ):
        member = user_factory(fullname="Mia Member")
        scoped = user_factory(fullname="Sam Scoped")
        outsider = user_factory(fullname="Otto Outsider")
        org = organization_factory(users=[{"name": member["name"], "capacity": "member"}])
        utils.assign_role_to_user(scoped["id"], const.Roles.Administrator.value, const.SCOPE_ORGANIZATION, org["id"])

        rows = _table_rows(app, sysadmin, tk.h.url_for("perm_manager.organization_user_roles_list", org_id=org["id"]))

        assert member["id"] in rows
        assert scoped["id"] in rows
        assert outsider["id"] not in rows
        assert "Administrator" in rows[scoped["id"]]["roles"]

        url = tk.h.url_for("perm_manager.organization_user_roles_list", org_id=org["id"], all=1)
        rows = _table_rows(app, sysadmin, url)

        assert outsider["id"] in rows

    def test_org_page_links_table_to_all_users_toggle(self, app, sysadmin, organization):
        url = tk.h.url_for("perm_manager.organization_user_roles_list", org_id=organization["id"], all=1)
        body = app.get(url, headers={"Authorization": sysadmin["token"]}, status=200).body

        assert 'id="all-users" data-module="perm-auto-submit" checked' in body
        assert "all=1" in body

    def test_user_link_uses_name(self, app, sysadmin, user):
        row = _table_rows(app, sysadmin, tk.h.url_for("perm_manager.user_roles_list"))[user["id"]]

        assert f'href="{tk.h.url_for("user.read", id=user["name"])}"' in row["display_name"]

    def test_role_badges_show_labels(self, app, sysadmin, user, test_role):
        utils.assign_role_to_user(user["id"], test_role["id"])

        row = _table_rows(app, sysadmin, tk.h.url_for("perm_manager.user_roles_list"))[user["id"]]

        assert f'<span class="badge bg-success">{test_role["label"]}</span>' in row["roles"]

    def test_edit_action_redirects_to_user_form(self, app, sysadmin, user):
        url = tk.h.url_for("perm_manager.user_roles_list")

        result = _row_action(app, sysadmin, url, "edit", {"id": user["id"]})

        assert result["redirect"] == tk.h.url_for("perm_manager.edit_user_role", user_id=user["id"])

    def test_org_edit_action_redirects_to_org_form(self, app, sysadmin, user, organization):
        url = tk.h.url_for("perm_manager.organization_user_roles_list", org_id=organization["id"])

        result = _row_action(app, sysadmin, url, "edit", {"id": user["id"]})

        assert result["redirect"] == tk.h.url_for(
            "perm_manager.organization_edit_user_role", org_id=organization["name"], user_id=user["id"]
        )


@pytest.mark.ckan_config("ckan.plugins", "permissions permissions_manager tables")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRolesList:
    def test_lists_roles_with_usage_counts(self, app, sysadmin, user, test_role):
        utils.assign_role_to_user(user["id"], test_role["id"])
        perm_model.RolePermission.create(test_role["id"], "read_any_dataset")

        rows = _table_rows(app, sysadmin, tk.h.url_for("perm_manager.role_list"))

        assert rows[test_role["id"]]["users"] == 1
        assert rows[test_role["id"]]["permissions"] == 1

    def test_default_role_has_lock_icon(self, app, sysadmin, test_role):
        rows = _table_rows(app, sysadmin, tk.h.url_for("perm_manager.role_list"))

        assert "fa-lock" in rows[const.Roles.Administrator.value]["label"]
        assert "fa-lock" not in rows[test_role["id"]]["label"]

    def test_delete_role(self, app, sysadmin, test_role):
        result = _row_action(app, sysadmin, tk.h.url_for("perm_manager.role_list"), "delete", {"id": test_role["id"]})

        assert result["success"]
        assert perm_model.Role.get(test_role["id"]) is None

    def test_default_role_cannot_be_deleted(self, app, sysadmin):
        role_id = const.Roles.Administrator.value

        result = _row_action(app, sysadmin, tk.h.url_for("perm_manager.role_list"), "delete", {"id": role_id})

        assert not result["success"]
        assert result["error"]
        assert perm_model.Role.get(role_id)

    def test_bulk_delete_keeps_going_after_a_failure(self, app, sysadmin, test_role):
        rows = [{"id": const.Roles.Administrator.value}, {"id": test_role["id"]}]

        result = app.post(
            tk.h.url_for("perm_manager.role_list"),
            data={"bulk_action": "delete", "rows": json.dumps(rows)},
            headers={"Authorization": sysadmin["token"]},
            status=200,
        ).json

        assert not result["success"]
        assert perm_model.Role.get(const.Roles.Administrator.value)
        assert perm_model.Role.get(test_role["id"]) is None

    def test_edit_action_redirects_to_role_form(self, app, sysadmin, test_role):
        result = _row_action(app, sysadmin, tk.h.url_for("perm_manager.role_list"), "edit", {"id": test_role["id"]})

        assert result["redirect"] == tk.h.url_for("perm_manager.role_edit", role_id=test_role["id"])


@pytest.mark.ckan_config("ckan.plugins", "permissions permissions_manager tables")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestChangeLog:
    def test_lists_changes_of_deleted_role(self, app, sysadmin, test_role):
        context = {"user": sysadmin["name"]}
        tk.get_action("permissions_update")(context, {"permissions": {"perm_1": {test_role["id"]: True}}})
        tk.get_action("permission_role_delete")(context, {"id": test_role["id"]})

        rows = list(_table_rows(app, sysadmin, tk.h.url_for("perm_manager.change_log")).values())
        deleted, granted = rows[0], rows[1]

        assert "Role deleted" in deleted["action"]
        assert deleted["role"] == test_role["label"]
        assert "Permissions: Permission 1" in deleted["details"]
        assert sysadmin["name"] in granted["actor"]
        assert "Permission granted" in granted["action"]
        assert granted["permission"] == "Permission 1"

    def test_role_update_shows_old_and_new_values(self, app, sysadmin, test_role):
        tk.get_action("permission_role_update")(
            {"user": sysadmin["name"]}, {"id": test_role["id"], "label": "Renamed", "description": "Updated"}
        )

        url = tk.h.url_for("perm_manager.change_log")
        [updated] = _table_rows(app, sysadmin, url, _like("action", "updated")).values()

        assert updated["role"] == "Renamed"
        assert f"<del>{test_role['label']}</del> &rarr; Renamed" in updated["details"]

    def test_user_role_changes_are_listed(self, app, sysadmin, user, organization):
        url = tk.h.url_for("perm_manager.organization_edit_user_role", org_id=organization["id"], user_id=user["id"])
        app.post(
            url,
            data={"roles": [const.Roles.Administrator.value]},
            headers={"Authorization": sysadmin["token"]},
            follow_redirects=False,
            status=302,
        )

        [assigned] = _table_rows(app, sysadmin, tk.h.url_for("perm_manager.change_log")).values()

        assert "Role assigned" in assigned["action"]
        assert assigned["role"] == "Administrator"
        assert f'href="{tk.h.url_for("user.read", id=user["name"])}"' in assigned["user"]
        assert sysadmin["name"] in assigned["actor"]
        assert f"Organization: {organization['title']}" in assigned["details"]

    def test_change_without_user_is_shown_as_system(self, app, sysadmin):
        perm_model.ChangeLog.create(const.ChangeAction.RoleCreated, "editor")

        [created] = _table_rows(app, sysadmin, tk.h.url_for("perm_manager.change_log")).values()

        assert created["actor"] == "System"


@pytest.mark.ckan_config("ckan.plugins", "permissions permissions_manager tables")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPermissionMatrix:
    def test_blocked_cell_has_no_toggle(self, app, sysadmin):
        body = app.get(
            tk.h.url_for("perm_manager.permission_list"), headers={"Authorization": sysadmin["token"]}, status=200
        ).body

        assert "Not allowed" in body
        assert 'id="anonymous-update_any_dataset"' not in body
        assert 'name="update_any_dataset|anonymous"' in body

    def test_unregistered_grants_notice(self, app, sysadmin):
        url = tk.h.url_for("perm_manager.permission_list")
        headers = {"Authorization": sysadmin["token"]}

        assert "ckan permissions orphans" not in app.get(url, headers=headers, status=200).body

        perm_model.RolePermission.create(const.Roles.Authenticated.value, "removed_permission")

        body = app.get(url, headers=headers, status=200).body

        assert "1 grant of a permission that no permission group defines" in body
        assert "ckan permissions orphans --delete" in body

    def test_toggles_have_accessible_name(self, app, sysadmin):
        body = app.get(
            tk.h.url_for("perm_manager.permission_list"), headers={"Authorization": sysadmin["token"]}, status=200
        ).body

        assert 'aria-label="Grant Read any dataset to Authenticated"' in body

    def test_dependency_error_keeps_submitted_state(self, app, sysadmin):
        body = app.post(
            tk.h.url_for("perm_manager.permission_list"),
            data={"update_any_dataset|authenticated": "set"},
            headers={"Authorization": sysadmin["token"]},
            status=200,
        ).body

        assert "Authenticated can&#39;t have Update any dataset without Read any dataset" in body
        assert "{&#39;" not in body
        assert re.search(r'<td class="perm-error">\s*<input [^>]*name="update_any_dataset\|authenticated">', body)

        toggle = re.search(r'<input type="checkbox" id="authenticated-update_any_dataset"[^>]*>', body)
        assert toggle
        assert 'data-submitted="true"' in toggle.group()
        assert 'aria-invalid="true"' in toggle.group()
        assert not perm_model.RolePermission.get("authenticated", "update_any_dataset")

    def test_rows_are_searchable_by_key(self, app, sysadmin):
        body = app.get(
            tk.h.url_for("perm_manager.permission_list"), headers={"Authorization": sysadmin["token"]}, status=200
        ).body

        assert re.search(r'data-search="[^"]*\bupdate_any_dataset\b', body)

    def test_export_modal_has_saved_permissions(self, app, sysadmin):
        perm_model.RolePermission.create(const.Roles.Authenticated.value, "read_any_dataset")

        body = app.get(
            tk.h.url_for("perm_manager.permission_list"), headers={"Authorization": sysadmin["token"]}, status=200
        ).body

        textarea = re.search(r'id="perm-export-modal".*?<textarea[^>]*>(.*?)</textarea>', body, re.S)
        assert textarea
        exported = json.loads(html.unescape(textarea.group(1)))
        assert exported["roles"]["authenticated"] == ["read_any_dataset"]


PAGES = [
    ("perm_manager.permission_list", {}),
    ("perm_manager.role_list", {}),
    ("perm_manager.role_add", {}),
    ("perm_manager.role_edit", {"role_id": "{role}"}),
    ("perm_manager.user_roles_list", {}),
    ("perm_manager.edit_user_role", {"user_id": "{user}"}),
    ("perm_manager.organization_user_roles_list", {"org_id": "{org}"}),
    ("perm_manager.organization_edit_user_role", {"org_id": "{org}", "user_id": "{user}"}),
    ("perm_manager.change_log", {}),
]

FORM_PAGES = [
    "perm_manager.permission_list",
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


@pytest.mark.ckan_config("ckan.plugins", "permissions permissions_manager tables")
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


@pytest.mark.ckan_config("ckan.plugins", "permissions permissions_manager tables")
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

    def test_edit_user_roles(self, app, sysadmin, user, test_role):
        url = tk.h.url_for("perm_manager.edit_user_role", user_id=user["id"])
        roles = [const.Roles.Administrator.value, test_role["id"]]

        self._post(app, sysadmin, url, {"roles": roles})

        assert sorted(tk.h.get_user_roles(user["id"])) == sorted(roles)

    def test_permissions_page_shows_dependencies(self, app, sysadmin):
        body = app.get(
            tk.h.url_for("perm_manager.permission_list"), headers={"Authorization": sysadmin["token"]}, status=200
        ).body

        assert "Requires:" in body
        assert 'data-permission="update_any_dataset"' in body
        assert 'data-depends-on="read_any_dataset"' in body


@pytest.mark.ckan_config("ckan.plugins", "permissions permissions_manager tables")
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

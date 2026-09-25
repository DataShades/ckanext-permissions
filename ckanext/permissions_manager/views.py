from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint, Response
from flask.views import MethodView

import ckan.plugins.toolkit as tk
from ckan import model, types
from ckan.lib.helpers import Page

from ckanext.permissions import const as perm_const
from ckanext.permissions import model as perm_model
from ckanext.permissions import utils

log = logging.getLogger(__name__)
perm_manager = Blueprint("perm_manager", __name__, url_prefix="/permissions")


USER_ROLES_PER_PAGE = 10
USER_ROLES_MAX_PER_PAGE = 100


@perm_manager.before_request
def before_request() -> None:
    try:
        tk.check_access("sysadmin", {"user": tk.current_user.name})
    except tk.NotAuthorized:
        tk.abort(403, tk._("Need to be system administrator to administer"))


class PermissionManagerView(MethodView):
    def get(self) -> str | Response:
        return tk.render(
            "perm_manager/list.html",
            extra_vars={
                "permission_groups": utils.get_permission_groups(),
            },
        )

    def post(self) -> Response:
        try:
            tk.get_action("permissions_update")({}, {"permissions": self._get_permissions()})
        except tk.ValidationError as e:
            tk.h.flash_error(str(e))
            return tk.redirect_to("perm_manager.permission_list")

        tk.h.flash_success("Permissions updated")

        return tk.redirect_to("perm_manager.permission_list")

    def _get_permissions(self) -> dict[str, dict[str, bool]]:
        permissions = {}

        for key in tk.request.form:
            if "|" not in key:
                continue

            values = tk.request.form.getlist(key)
            permission, _, role_id = key.partition("|")

            if permission not in permissions:
                permissions[permission] = {}

            permissions[permission][role_id] = "set" in values

        return permissions


class RoleManagerView(MethodView):
    def get(self) -> str | Response:
        return tk.render(
            "perm_manager/role_list.html",
            extra_vars={
                "roles": sorted(perm_model.Role.all(), key=lambda x: x["label"]),
            },
        )


class RoleAdd(MethodView):
    def get(self) -> str | Response:
        return tk.render(
            "perm_manager/add_role.html",
            extra_vars={"errors": {}, "data": {}},
        )

    def post(self) -> str | Response:
        payload = dict(tk.request.form)

        try:
            tk.get_action("permission_role_create")({}, payload)
        except tk.NotAuthorized as e:
            return tk.abort(403, str(e))
        except tk.ValidationError as e:
            return tk.render(
                "perm_manager/add_role.html",
                extra_vars={"errors": e.error_dict, "data": payload},
            )

        tk.h.flash_success("Role has been created")

        return tk.redirect_to("perm_manager.role_list")


class RoleDelete(MethodView):
    def post(self) -> Response:
        payload = dict(tk.request.form)

        try:
            tk.get_action("permission_role_delete")({}, payload)
        except tk.ValidationError as e:
            tk.h.flash_error(str(e))
        else:
            tk.h.flash_success("Role has been deleted")

        return tk.redirect_to("perm_manager.role_list")


class RoleEdit(MethodView):
    def get(self, role_id: str) -> str | Response:
        return tk.render(
            "perm_manager/edit_role.html",
            extra_vars={"role": _get_role(role_id), "errors": {}, "data": {}},
        )

    def post(self, role_id: str) -> str | Response:
        role = _get_role(role_id)
        payload = dict(tk.request.form)

        try:
            tk.get_action("permission_role_update")(
                {},
                {
                    "id": role_id,
                    "description": payload.get("description"),
                },
            )
        except tk.ValidationError as e:
            return tk.render(
                "perm_manager/edit_role.html",
                extra_vars={
                    "role": role,
                    "errors": e.error_dict,
                    "data": payload,
                },
            )

        tk.h.flash_success("Role has been updated")

        return tk.redirect_to("perm_manager.role_list")


class BaseUserRolesList(MethodView):
    def _get_user_with_roles(
        self, scope: str = perm_const.SCOPE_GLOBAL, scope_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get all active users and their roles."""
        result: list[dict[str, Any]] = [
            {
                "id": user.id,
                "display_name": user.display_name,
                "roles": tk.h.get_user_roles(user.id, scope, scope_id),
            }
            for user in self._get_active_users()
        ]

        return self._apply_filters(result)

    def _get_active_users(self) -> list[model.User]:
        """Get all active users and sort them by display name."""
        return sorted(
            (model.Session.query(model.User).filter(model.User.state == model.State.ACTIVE).all()),
            key=lambda x: x.display_name,
        )

    def _apply_filters(self, users: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply filters based on username and role."""
        q = tk.request.args.get("q", "").strip()
        role_filter = tk.request.args.get("role", "").strip()

        if q:
            users = [user for user in users if q.lower() in user["display_name"].lower() or q.lower() in user["roles"]]

        if role_filter:
            users = [user for user in users if role_filter in user["roles"]]

        return users


class UserRolesList(BaseUserRolesList):
    def get(self) -> str | Response:
        users = self._get_user_with_roles()
        page = Page(
            collection=users,
            page=tk.h.get_page_number(tk.request.args),
            url=tk.h.pager_url,
            item_count=len(users),
            items_per_page=_get_limit(),
        )
        return tk.render("perm_manager/user_roles_list.html", extra_vars={"page": page})


class OrganizationUserRolesList(BaseUserRolesList):
    def get(self, org_id: str) -> str | Response:
        org_dict = _get_org_dict(org_id)
        users = self._get_user_with_roles(scope=perm_const.SCOPE_ORGANIZATION, scope_id=org_dict["id"])

        def _pager_url(**kwargs: Any) -> str:
            return tk.h.url_for("perm_manager.organization_user_roles_list", org_id=org_id, **kwargs)

        page = Page(
            collection=users,
            page=tk.h.get_page_number(tk.request.args),
            url=_pager_url,
            item_count=len(users),
            items_per_page=_get_limit(),
        )

        return tk.render(
            "perm_manager/organization/user_roles_list.html",
            extra_vars={
                "group_dict": org_dict,
                "group_type": "organization",
                "page": page,
            },
        )


class EditUserRole(MethodView):
    def __init__(self):
        self.schema = {
            "roles": [tk.get_validator(validator) for validator in ["not_missing", "list_of_strings", "roles_exists"]]
        }

    def get(self, user_id: str) -> str | Response:
        user = model.User.get(user_id)

        if not user:
            return tk.abort(404, "User not found")

        return tk.render(
            "perm_manager/edit_user_roles.html",
            extra_vars={
                "user": user,
                "data": {"roles": ",".join(tk.h.get_user_roles(user.id))},
                "errors": {},
            },
        )

    def post(self, user_id: str) -> str | Response:
        return self._update_user_roles(user_id, perm_const.SCOPE_GLOBAL)

    def _update_user_roles(self, user_id: str, scope: str, scope_id: str | None = None) -> str | Response:
        payload = {"roles": tk.request.form.getlist("roles")}

        user = model.User.get(user_id)

        if not user:
            tk.abort(404, "User not found")

        data, errors = tk.navl_validate(payload, self.schema)

        if errors:
            return tk.render(
                "perm_manager/edit_user_roles.html",
                extra_vars={"user": user, "data": data, "errors": errors},
            )

        perm_model.UserRole.clear_user_roles(user.id, scope, scope_id, commit=False)

        for role in data["roles"]:
            perm_model.UserRole.create(user_id=user.id, role=role, scope=scope, scope_id=scope_id, commit=False)

        model.Session.commit()

        tk.h.flash_success("User roles updated")

        return (
            tk.redirect_to("perm_manager.user_roles_list")
            if scope == perm_const.SCOPE_GLOBAL
            else tk.redirect_to("perm_manager.organization_user_roles_list", org_id=scope_id)
        )


class OrganizationEditUserRole(EditUserRole):
    def get(self, org_id: str, user_id: str) -> str | Response:
        user = model.User.get(user_id)

        if not user:
            return tk.abort(404, "User not found")

        org_dict = _get_org_dict(org_id)
        scope = perm_const.SCOPE_ORGANIZATION

        return tk.render(
            "perm_manager/organization/edit_user_roles.html",
            extra_vars={
                "user": user,
                "data": {"roles": ",".join(tk.h.get_user_roles(user.id, scope, org_dict["id"]))},
                "errors": {},
                "group_dict": org_dict,
                "group_type": scope,
            },
        )

    def post(self, org_id: str, user_id: str) -> str | Response:
        org_dict = _get_org_dict(org_id)

        return self._update_user_roles(user_id, perm_const.SCOPE_ORGANIZATION, org_dict["id"])


def _get_limit() -> int:
    try:
        limit = tk.asint(tk.request.args.get("limit", USER_ROLES_PER_PAGE))
    except ValueError:
        return USER_ROLES_PER_PAGE

    return min(max(limit, 1), USER_ROLES_MAX_PER_PAGE)


def _get_role(role_id: str) -> perm_model.Role:
    role = perm_model.Role.get(role_id)

    if not role:
        tk.abort(404, tk._("Role not found"))

    return role


def _get_org_dict(org_id: str) -> dict[str, Any]:
    context = types.Context(user=tk.current_user.name, for_view=True)

    try:
        return tk.get_action("organization_show")(context, {"id": org_id, "include_datasets": False})
    except (tk.ObjectNotFound, tk.NotAuthorized):
        tk.abort(404, tk._("Organization not found"))


perm_manager.add_url_rule("/manage", view_func=PermissionManagerView.as_view("permission_list"))

perm_manager.add_url_rule("/roles", view_func=RoleManagerView.as_view("role_list"))
perm_manager.add_url_rule("/roles/add", view_func=RoleAdd.as_view("role_add"))
perm_manager.add_url_rule("/roles/delete", view_func=RoleDelete.as_view("role_delete"))
perm_manager.add_url_rule("/roles/<role_id>", view_func=RoleEdit.as_view("role_edit"))

# organization user roles
perm_manager.add_url_rule(
    "/organization/user-roles/<org_id>",
    view_func=OrganizationUserRolesList.as_view("organization_user_roles_list"),
)
perm_manager.add_url_rule(
    "/organization/user-roles/<org_id>/<user_id>",
    view_func=OrganizationEditUserRole.as_view("organization_edit_user_role"),
)

perm_manager.add_url_rule("/user-roles", view_func=UserRolesList.as_view("user_roles_list"))
perm_manager.add_url_rule("/user-roles/<user_id>", view_func=EditUserRole.as_view("edit_user_role"))

blueprints = [perm_manager]

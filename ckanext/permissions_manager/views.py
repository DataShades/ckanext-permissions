from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint, Response
from flask.views import MethodView

import ckan.plugins.toolkit as tk
from ckan import model, types

from ckanext.tables.generics import TableDispatchMixin
from ckanext.tables.shared import GenericTableView

from ckanext.permissions import const as perm_const
from ckanext.permissions import model as perm_model
from ckanext.permissions import utils
from ckanext.permissions_manager.tables import (
    OrganizationUserRolesTable,
    RolesTable,
    UserRolesTable,
    flatten_errors,
)

log = logging.getLogger(__name__)
perm_manager = Blueprint("perm_manager", __name__, url_prefix="/permissions")


@perm_manager.before_request
def before_request() -> None:
    try:
        tk.check_access("sysadmin", {"user": tk.current_user.name})
    except tk.NotAuthorized:
        tk.abort(403, tk._("Need to be system administrator to administer"))


class PermissionManagerView(MethodView):
    def get(self) -> str | Response:
        return self._render()

    def post(self) -> str | Response:
        permissions = self._get_permissions()

        try:
            tk.get_action("permissions_update")({}, {"permissions": permissions})
        except tk.ValidationError as e:
            return self._render(permissions, e.error_dict)

        tk.h.flash_success(tk._("Permissions updated"))

        return tk.redirect_to("perm_manager.permission_list")

    def _render(
        self,
        submitted: dict[str, dict[str, bool]] | None = None,
        errors: dict[str, Any] | None = None,
    ) -> str:
        errors = errors or {}

        return tk.render(
            "perm_manager/list.html",
            extra_vars={
                "permission_groups": utils.get_permission_groups(),
                "permissions": utils.get_permissions(),
                "submitted": submitted or {},
                "error_messages": flatten_errors(errors),
                "error_cells": self._get_error_cells(submitted or {}, errors),
            },
        )

    def _get_error_cells(self, submitted: dict[str, dict[str, bool]], errors: dict[str, Any]) -> set[str]:
        """Return the `permission|role` cells the admin changed in rows that failed validation."""
        cells = set()

        for permission, roles in submitted.items():
            if permission not in errors:
                continue

            for role_id, granted in roles.items():
                if granted != bool(perm_model.RolePermission.get(role_id, permission)):
                    cells.add(f"{permission}|{role_id}")

        return cells

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

        tk.h.flash_success(tk._("Role has been created"))

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
                    "label": payload.get("label"),
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

        tk.h.flash_success(tk._("Role has been updated"))

        return tk.redirect_to("perm_manager.role_list")


class OrganizationUserRolesList(TableDispatchMixin, MethodView):
    def get(self, org_id: str) -> str | Response | tuple[Response, int]:
        return self._dispatch_get(self._get_table(org_id))

    def post(self, org_id: str) -> Response:
        return self._dispatch_post(self._get_table(org_id))

    def _get_table(self, org_id: str) -> OrganizationUserRolesTable:
        return OrganizationUserRolesTable(_get_org_dict(org_id), show_all=tk.asbool(tk.request.args.get("all")))

    def _render_full_page(self, table: OrganizationUserRolesTable) -> str:  # type: ignore[override]
        return table.render_table(group_dict=table.group_dict, group_type=perm_const.SCOPE_ORGANIZATION)


class EditUserRole(MethodView):
    def __init__(self):
        self.schema = {
            "roles": [tk.get_validator(validator) for validator in ["not_missing", "list_of_strings", "roles_exists"]]
        }

    def get(self, user_id: str) -> str | Response:
        user = model.User.get(user_id)

        if not user:
            return tk.abort(404, tk._("User not found"))

        return self._render_form(user, {"roles": tk.h.get_user_roles(user.id)}, {})

    def post(self, user_id: str) -> str | Response:
        return self._update_user_roles(user_id)

    def _render_form(
        self,
        user: model.User,
        data: dict[str, Any],
        errors: dict[str, Any],
        group_dict: dict[str, Any] | None = None,
    ) -> str:
        if not group_dict:
            return tk.render(
                "perm_manager/edit_user_roles.html",
                extra_vars={"user": user, "data": data, "errors": errors},
            )

        return tk.render(
            "perm_manager/organization/edit_user_roles.html",
            extra_vars={
                "user": user,
                "data": data,
                "errors": errors,
                "group_dict": group_dict,
                "group_type": perm_const.SCOPE_ORGANIZATION,
            },
        )

    def _update_user_roles(self, user_id: str, group_dict: dict[str, Any] | None = None) -> str | Response:
        payload = {"roles": tk.request.form.getlist("roles")}
        scope = perm_const.SCOPE_ORGANIZATION if group_dict else perm_const.SCOPE_GLOBAL
        scope_id = group_dict["id"] if group_dict else None

        user = model.User.get(user_id)

        if not user:
            tk.abort(404, tk._("User not found"))

        data, errors = tk.navl_validate(payload, self.schema)

        if errors:
            return self._render_form(user, payload, errors, group_dict)

        old_roles = set(tk.h.get_user_roles(user.id, scope, scope_id))

        perm_model.UserRole.clear_user_roles(user.id, scope, scope_id, commit=False)

        for role in data["roles"]:
            perm_model.UserRole.create(user_id=user.id, role=role, scope=scope, scope_id=scope_id, commit=False)

        model.Session.commit()

        new_roles = set(data["roles"])

        if old_roles != new_roles:
            log.info(
                "User roles updated: user=%s scope=%s scope_id=%s added=%s removed=%s actor=%s",
                user.name,
                scope,
                scope_id,
                sorted(new_roles - old_roles),
                sorted(old_roles - new_roles),
                tk.current_user.name,
            )

        tk.h.flash_success(tk._("User roles updated"))

        return (
            tk.redirect_to("perm_manager.user_roles_list")
            if scope == perm_const.SCOPE_GLOBAL
            else tk.redirect_to("perm_manager.organization_user_roles_list", org_id=scope_id)
        )


class OrganizationEditUserRole(EditUserRole):
    def get(self, org_id: str, user_id: str) -> str | Response:
        user = model.User.get(user_id)

        if not user:
            return tk.abort(404, tk._("User not found"))

        org_dict = _get_org_dict(org_id)
        roles = tk.h.get_user_roles(user.id, perm_const.SCOPE_ORGANIZATION, org_dict["id"])

        return self._render_form(user, {"roles": roles}, {}, org_dict)

    def post(self, org_id: str, user_id: str) -> str | Response:
        return self._update_user_roles(user_id, _get_org_dict(org_id))


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

perm_manager.add_url_rule("/roles", view_func=GenericTableView.as_view("role_list", table=RolesTable))
perm_manager.add_url_rule("/roles/add", view_func=RoleAdd.as_view("role_add"))
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

perm_manager.add_url_rule(
    "/user-roles",
    view_func=GenericTableView.as_view("user_roles_list", table=UserRolesTable),
)
perm_manager.add_url_rule("/user-roles/<user_id>", view_func=EditUserRole.as_view("edit_user_role"))

blueprints = [perm_manager]

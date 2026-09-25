from __future__ import annotations

import logging
import math
from typing import Any

import sqlalchemy as sa
from flask import Blueprint, Response
from flask.views import MethodView
from sqlalchemy.orm import Query

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
                "permissions": utils.get_permissions(),
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
                "user_counts": _count_by_role(perm_model.UserRole.user_id),
                "permission_counts": _count_by_role(perm_model.RolePermission.permission),
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
    def _get_page(self, url: Any, scope: str, scope_id: str | None = None) -> Page:
        """Get a page of active users with their roles, filtered by name and role."""
        query = self._get_users_query(scope, scope_id)
        item_count = query.count()
        limit = _get_limit()
        last_page = max(math.ceil(item_count / limit), 1)
        page_number = min(tk.h.get_page_number(tk.request.args), last_page)

        users = query.offset((page_number - 1) * limit).limit(limit).all()
        roles = perm_model.UserRole.get_for_users([user.id for user in users], scope, scope_id)

        return Page(
            collection=[
                {"id": user.id, "display_name": user.display_name, "roles": roles.get(user.id, [])} for user in users
            ],
            page=page_number,
            url=url,
            item_count=item_count,
            items_per_page=limit,
            presliced_list=True,
        )

    def _get_users_query(self, scope: str, scope_id: str | None) -> Query:
        display_name = sa.case(
            (sa.func.trim(model.User.fullname) != "", model.User.fullname),
            else_=model.User.name,
        )
        query = model.Session.query(model.User).filter(
            model.User.state == model.State.ACTIVE,
            sa.func.trim(model.User.email) != "",
        )

        q = tk.request.args.get("q", "").strip().lower()
        role_filter = tk.request.args.get("role", "").strip()

        if q:
            query = query.filter(
                sa.or_(
                    sa.func.lower(display_name).contains(q, autoescape=True),
                    self._has_role(q, scope, scope_id),
                )
            )

        if role_filter:
            query = query.filter(self._has_role(role_filter, scope, scope_id))

        if scope_id and not tk.asbool(tk.request.args.get("all")):
            query = query.filter(sa.or_(self._is_member(scope_id), self._has_any_role(scope, scope_id)))

        return query.order_by(sa.func.lower(display_name), model.User.name)

    def _has_role(self, role_id: str, scope: str, scope_id: str | None) -> Any:
        return self._has_any_role(scope, scope_id, perm_model.UserRole.role_id == role_id)

    def _has_any_role(self, scope: str, scope_id: str | None, *extra: Any) -> Any:
        user_role = perm_model.UserRole
        conditions = [user_role.user_id == model.User.id, user_role.scope == scope, *extra]

        if scope_id:
            conditions.append(user_role.scope_id == scope_id)

        return sa.exists().where(*conditions)

    def _is_member(self, org_id: str) -> Any:
        return sa.exists().where(
            model.Member.table_id == model.User.id,
            model.Member.table_name == "user",
            model.Member.group_id == org_id,
            model.Member.state == model.State.ACTIVE,
        )


class UserRolesList(BaseUserRolesList):
    def get(self) -> str | Response:
        page = self._get_page(tk.h.pager_url, perm_const.SCOPE_GLOBAL)

        return tk.render("perm_manager/user_roles_list.html", extra_vars={"page": page})


class OrganizationUserRolesList(BaseUserRolesList):
    def get(self, org_id: str) -> str | Response:
        org_dict = _get_org_dict(org_id)

        def _pager_url(**kwargs: Any) -> str:
            return tk.h.url_for("perm_manager.organization_user_roles_list", org_id=org_id, **kwargs)

        page = self._get_page(_pager_url, perm_const.SCOPE_ORGANIZATION, org_dict["id"])

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


def _count_by_role(column: Any) -> dict[str, int]:
    role_id = column.class_.role_id
    query = model.Session.query(role_id, sa.func.count(sa.distinct(column))).group_by(role_id)

    return dict(query.all())


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

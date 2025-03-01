from __future__ import annotations

import logging
from typing import Union

from flask import Blueprint, Response
from flask.views import MethodView

import ckan.model as model
import ckan.plugins.toolkit as tk

from ckanext.ap_main.utils import ap_before_request

from ckanext.permissions import model as perm_model
from ckanext.permissions import utils

log = logging.getLogger(__name__)
perm_manager = Blueprint(
    "perm_manager", __name__, url_prefix="/admin-panel/permissions"
)

perm_manager.before_request(ap_before_request)


class PermissionManagerView(MethodView):
    def get(self) -> Union[str, Response]:
        return tk.render(
            "perm_manager/list.html",
            extra_vars={
                "permission_groups": utils.get_permission_groups(),
            },
        )

    def post(self) -> Response:
        tk.get_action("permissions_update")(
            {}, {"permissions": self._get_permissions()}
        )

        tk.h.flash_success("Permissions updated")

        return tk.redirect_to("perm_manager.permission_list")

    def _get_permissions(self) -> dict[str, dict[str, bool]]:
        permissions = {}

        for key in tk.request.form.keys():
            if "|" not in key:
                continue

            values = tk.request.form.getlist(key)
            permission, role_id = key.split("|")

            if permission not in permissions:
                permissions[permission] = {}

            permissions[permission][role_id] = "set" in values

        return permissions


class RoleManagerView(MethodView):
    def get(self) -> Union[str, Response]:
        return tk.render(
            "perm_manager/role_list.html",
            extra_vars={
                "roles": sorted(perm_model.Role.all(), key=lambda x: x["label"]),
            },
        )


class RoleAdd(MethodView):
    def get(self) -> Union[str, Response]:
        return tk.render(
            "perm_manager/add_role.html",
            extra_vars={"errors": {}, "data": {}},
        )

    def post(self) -> Union[str, Response]:
        payload = dict(tk.request.form)

        tk.get_or_bust(payload, ["id", "label", "description"])

        try:
            tk.get_action("permission_role_create")({}, payload)
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

        tk.get_or_bust(payload, ["id"])

        try:
            tk.get_action("permission_role_delete")({}, payload)
        except tk.ValidationError as e:
            tk.h.flash_error(str(e))
        else:
            tk.h.flash_success("Role has been deleted")

        return tk.redirect_to("perm_manager.role_list")


class RoleEdit(MethodView):
    def get(self, role_id: str) -> Union[str, Response]:
        return tk.render(
            "perm_manager/edit_role.html",
            extra_vars={"role": perm_model.Role.get(role_id), "errors": {}, "data": {}},
        )

    def post(self, role_id: str) -> Union[str, Response]:
        payload = dict(tk.request.form)

        tk.get_or_bust(payload, "description")

        try:
            tk.get_action("permission_role_update")(
                {},
                {
                    "id": role_id,
                    "description": payload["description"],
                },
            )
        except tk.ValidationError as e:
            return tk.render(
                "perm_manager/edit_role.html",
                extra_vars={
                    "role": perm_model.Role.get(role_id),
                    "errors": e.error_dict,
                    "data": payload,
                },
            )

        tk.h.flash_success("Role has been updated")

        return tk.redirect_to("perm_manager.role_list")


class UserRolesList(MethodView):
    def get(self) -> Union[str, Response]:
        return tk.render(
            "perm_manager/user_roles_list.html",
            extra_vars={
                "users": self._get_active_users(),
            },
        )

    def _get_active_users(self) -> list[model.User]:
        return (
            model.Session.query(model.User)
            .filter(model.User.state == model.State.ACTIVE)
            .all()
        )


class EditUserRole(MethodView):
    def __init__(self):
        self.fields = [
            {
                "field_name": "roles",
                "label": "Roles",
                "help_text": "Select roles for the user",
                "choices": [
                    {"value": role_id, "label": role_label}
                    for role_id, role_label in utils.get_registered_roles().items()
                ],
                "validators": "not_missing list_of_strings roles_exists",
                "form_snippet": "tom_select.html",
                "form_attrs": {"multiple": "true", "data-module-create": "false"},
            }
        ]

        self.schema = {
            field["field_name"]: [
                tk.get_validator(validator) for validator in field["validators"].split()
            ]
            for field in self.fields
        }

    def get(self, user_id: str) -> Union[str, Response]:
        user = model.User.get(user_id)

        if not user:
            return tk.abort(404, "User not found")

        return tk.render(
            "perm_manager/edit_user_roles.html",
            extra_vars={
                "user": user,
                "data": {"roles": ",".join(tk.h.get_user_roles(user.id))},
                "errors": {},
                "fields": self.fields,
            },
        )

    def post(self, user_id: str) -> Union[str, Response]:
        payload = {"roles": tk.request.form.getlist("roles")}

        user = model.User.get(user_id)

        if not user:
            tk.abort(404, "User not found")

        data, errors = tk.navl_validate(payload, self.schema)

        if errors:
            return tk.render(
                "perm_manager/edit_user_roles.html",
                extra_vars={
                    "user": user,
                    "data": data,
                    "errors": errors,
                    "fields": self.fields,
                },
            )

        perm_model.UserRole.clear_user_roles(user.id)

        for role in data["roles"]:
            perm_model.UserRole.create(user_id=user.id, role=role)

        model.Session.commit()

        tk.h.flash_success("User roles updated")

        return tk.redirect_to("perm_manager.edit_user_role", user_id=user_id)


perm_manager.add_url_rule(
    "/manage", view_func=PermissionManagerView.as_view("permission_list")
)

perm_manager.add_url_rule("/roles", view_func=RoleManagerView.as_view("role_list"))
perm_manager.add_url_rule("/roles/add", view_func=RoleAdd.as_view("role_add"))
perm_manager.add_url_rule("/roles/delete", view_func=RoleDelete.as_view("role_delete"))
perm_manager.add_url_rule("/roles/<role_id>", view_func=RoleEdit.as_view("role_edit"))

perm_manager.add_url_rule(
    "/user-roles", view_func=UserRolesList.as_view("user_roles_list")
)
perm_manager.add_url_rule(
    "/user-roles/<user_id>", view_func=EditUserRole.as_view("edit_user_role")
)

blueprints = [perm_manager]

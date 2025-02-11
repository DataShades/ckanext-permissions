from __future__ import annotations

import logging
from typing import Union

from flask import Blueprint, Response
from flask.views import MethodView

import ckan.plugins.toolkit as tk

from ckanext.ap_main.utils import ap_before_request

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
        permissions = self._get_permissions()

        for permission, value in tk.request.form.items():
            if "|" not in permission:
                continue

            permission_key, role = permission.split("|")
            permission = permissions[permission_key]

            tk.get_action("permission_define")(
                {},
                {
                    "key": permission_key,
                    "label": permissions[permission_key]["label"],
                    "description": permissions[permission_key].get("description", ""),
                    "group": permissions[permission_key]["group"],
                    "roles": [
                        {
                            "role": role,
                            "permission": permission_key,
                            "state": tk.request.form[permission],
                        }
                        for role in tk.request.form.getlist(permission)
                    ],
                },
            )

        return tk.redirect_to("perm_manager.list")

        # "key": [not_empty, unicode_safe],
        # "label": [ignore_empty, unicode_safe],
        # "description": [ignore_empty, unicode_safe],
        # "group": [not_empty, unicode_safe, permission_group_exists],
        # "roles": role_schema,

        # "role": [not_empty, unicode_safe, permission_role_is_allowed],
        # "permission": [not_empty, unicode_safe, permission_exists],
        # "state": [not_empty, unicode_safe, one_of(perm_const.ROLE_STATES)],

    def _get_permissions(self):
        permission_groups = utils.get_permission_groups()

        result = {}

        for permission_group in permission_groups:
            for permission in permission_group["permissions"]:
                permission["group"] = permission_group["name"]
                result[permission["key"]] = permission

        return result


perm_manager.add_url_rule("/manage", view_func=PermissionManagerView.as_view("list"))

blueprints = [perm_manager]

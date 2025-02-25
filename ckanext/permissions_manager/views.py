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
        for key in tk.request.form.keys():
            if "|" not in key:
                continue

            values = tk.request.form.getlist(key)
            permission, role = key.split("|")

            role_perm = perm_model.RolePermission.get(role=role, permission=permission)

            if "set" in values and not role_perm:
                perm_model.RolePermission.create(role=role, permission=permission)
            else:
                role_perm.delete() if role_perm else None

        model.Session.commit()

        tk.h.flash_success("Permissions updated")

        return tk.redirect_to("perm_manager.list")


perm_manager.add_url_rule("/manage", view_func=PermissionManagerView.as_view("list"))

blueprints = [perm_manager]

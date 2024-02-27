from __future__ import annotations

import logging
from typing import Callable, Union

from flask import Blueprint, Response
from flask.views import MethodView

import ckan.plugins.toolkit as tk
from ckan.logic import parse_params

from ckanext.ap_main.utils import ap_before_request
from ckanext.collection.shared import get_collection

log = logging.getLogger(__name__)
perm_manager = Blueprint(
    "perm_manager", __name__, url_prefix="/admin-panel/permissions"
)
perm_manager.before_request(ap_before_request)


class FileManagerView(MethodView):
    def get(self) -> Union[str, Response]:
        kwargs = parse_params(tk.request.args)
        kwargs.update({"page": 1, "rows_per_page": 6})

        return tk.render(
            "perm_manager/list.html",
            extra_vars={
                "collection": get_collection(
                    "permissions-manager",
                    kwargs,
                ),
            },
        )

    def post(self) -> Response:
        bulk_action = tk.request.form.get("bulk-action")
        file_ids = tk.request.form.getlist("entity_id")

        action_func = self._get_bulk_action(bulk_action) if bulk_action else None

        if not action_func:
            tk.h.flash_error(tk._("The bulk action is not implemented"))
            return tk.redirect_to("perm_manager.list")

        for file_id in file_ids:
            try:
                action_func(file_id)
            except tk.ValidationError as e:
                tk.h.flash_error(str(e))

        return tk.redirect_to("perm_manager.list")

    def _get_bulk_action(self, value: str) -> Callable[[str], None] | None:
        return {
            "1": self._remove_file,
        }.get(value)

    def _remove_file(self, file_id: str) -> None:
        tk.get_action("files_file_delete")(
            {"ignore_auth": True},
            {"id": file_id},
        )


class FileManagerUploadView(MethodView):
    def post(self):
        file = tk.request.files.get("upload")

        if not file:
            tk.h.flash_error(tk._("Missing file object"))
            return tk.redirect_to("perm_manager.list")

        try:
            tk.get_action("files_file_create")(
                {"ignore_auth": True},
                {
                    "name": file.filename,
                    "upload": file,
                },
            )
        except (tk.ValidationError, OSError) as e:
            tk.h.flash_error(str(e.error_summary))
            return tk.redirect_to("perm_manager.list")

        tk.h.flash_success(tk._("File has been uploaded!"))
        return tk.redirect_to("perm_manager.list")


class FileManagerDeleteView(MethodView):
    def post(self, file_id: str):
        try:
            tk.get_action("files_file_delete")({"ignore_auth": True}, {"id": file_id})
        except (tk.ValidationError, OSError) as e:
            tk.h.flash_error(str(e.error_summary))
            return tk.redirect_to("perm_manager.list")

        tk.h.flash_success(tk._("File has been deleted!"))
        return tk.redirect_to("perm_manager.list")


perm_manager.add_url_rule("/manage", view_func=FileManagerView.as_view("list"))

blueprints = [perm_manager]

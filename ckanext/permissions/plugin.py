from __future__ import annotations

import ckan.plugins as p
import ckan.plugins.toolkit as tk

from ckanext.permissions import types, utils


@tk.blanket.validators
@tk.blanket.actions
@tk.blanket.helpers
class PermissionsPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)

    _permissions_groups: types.PermissionGroup | None = None

    # IConfigurer

    def update_config(self, config_: tk.CKANConfig):
        if not PermissionsPlugin._permissions_groups:  # type: ignore
            PermissionsPlugin._permissions_groups = list(  # type: ignore
                utils.parse_permission_group_schemas().values()
            )

        tk.add_template_directory(config_, "templates")
        tk.add_public_directory(config_, "public")
        tk.add_resource("assets", "permissions")

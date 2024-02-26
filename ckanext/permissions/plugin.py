from __future__ import annotations

import ckan.plugins as p
import ckan.plugins.toolkit as tk

from ckanext.permissions.interfaces import IPermissions

# from ckanext.permissions.utils import collect_permission_groups


@tk.blanket.validators
@tk.blanket.actions
class PermissionsPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(IPermissions)

    permissions = None

    # IConfigurer

    def update_config(self, config_: tk.CKANConfig):
        tk.add_template_directory(config_, "templates")
        tk.add_public_directory(config_, "public")
        tk.add_resource("assets", "permissions")

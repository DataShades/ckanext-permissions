from __future__ import annotations

import ckan.plugins as p
import ckan.plugins.toolkit as tk


@tk.blanket.validators
@tk.blanket.actions
@tk.blanket.helpers
class PermissionsPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)

    permissions = None

    # IConfigurer

    def update_config(self, config_: tk.CKANConfig):
        tk.add_template_directory(config_, "templates")
        tk.add_public_directory(config_, "public")
        tk.add_resource("assets", "permissions")

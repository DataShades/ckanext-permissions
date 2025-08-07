from __future__ import annotations

import ckan.plugins as p
import ckan.plugins.toolkit as tk
import ckan.types as types


@tk.blanket.blueprints
@tk.blanket.helpers
class PermissionsManagerPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ISignal)

    # IConfigurer

    def update_config(self, config_):
        tk.add_template_directory(config_, "templates")
        tk.add_public_directory(config_, "public")
        tk.add_resource("assets", "permissions_manager")

    # ISignal

    def get_signal_subscriptions(self) -> types.SignalMapping:
        return {
            tk.signals.ckanext.signal("ap_main:collect_config_sections"): [self.collect_config_sections_subs],
        }

    @staticmethod
    def collect_config_sections_subs(sender: None):
        return {
            "name": "Permissions",
            "configs": [
                {
                    "name": "Permissions manager",
                    "blueprint": "perm_manager.permission_list",
                    "info": "Manage portal permissions",
                },
                {
                    "name": "Roles manager",
                    "blueprint": "perm_manager.role_list",
                    "info": "Manage portal roles",
                },
                {
                    "name": "User roles list",
                    "blueprint": "perm_manager.user_roles_list",
                },
            ],
        }

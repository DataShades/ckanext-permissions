from __future__ import annotations

from typing import ClassVar

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan.lib.plugins import DefaultTranslation

from ckanext.permissions import implementation, utils
from ckanext.permissions import types as perm_types


@tk.blanket.cli
@tk.blanket.validators
@tk.blanket.actions
@tk.blanket.helpers
@tk.blanket.auth_functions
@tk.blanket.config_declarations
class PermissionsPlugin(implementation.PermissionLabels, DefaultTranslation, p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ITranslation)

    _permissions_groups: ClassVar[list[perm_types.PermissionGroup]] = []
    _permissions: ClassVar[dict[str, perm_types.PermissionDefinition]] = {}
    _declared_roles: ClassVar[dict[str, perm_types.RoleDefinition]] = {}
    _roles_loaded: ClassVar[bool] = False

    # IConfigurer

    def update_config(self, config_: tk.CKANConfig):
        plugin = type(self)

        if not plugin._permissions_groups:
            plugin._permissions_groups = list(utils.parse_permission_group_schemas().values())
            plugin._permissions = {
                permission["key"]: permission
                for group in plugin._permissions_groups
                for permission in group["permissions"]
            }

        if not plugin._roles_loaded:
            plugin._declared_roles = utils.parse_declared_roles()
            plugin._roles_loaded = True

        tk.add_template_directory(config_, "templates")

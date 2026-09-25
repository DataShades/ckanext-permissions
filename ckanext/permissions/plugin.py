from __future__ import annotations

from typing import ClassVar

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan import types

from ckanext.permissions import const as perm_const
from ckanext.permissions import implementation, utils
from ckanext.permissions import types as perm_types


@tk.blanket.cli
@tk.blanket.validators
@tk.blanket.actions
@tk.blanket.helpers
@tk.blanket.auth_functions
@tk.blanket.config_declarations
class PermissionsPlugin(implementation.PermissionLabels, p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ISignal)

    _permissions_groups: ClassVar[list[perm_types.PermissionGroup]] = []
    _permissions: ClassVar[dict[str, perm_types.PermissionDefinition]] = {}

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

        tk.add_template_directory(config_, "templates")

    # ISignal

    def get_signal_subscriptions(self) -> types.SignalMapping:
        return {tk.signals.action_succeeded: [self.assign_default_user_role]}

    @staticmethod
    def assign_default_user_role(
        action_name: str,
        context: types.Context,
        data_dict: types.DataDict,
        result: types.DataDict,
    ):
        """Assign the default user role to a new user.

        Args:
            action_name: The name of the action
            context: The action context
            data_dict: The action payload
            result: The action result
        """
        if action_name != "user_create":
            return

        utils.assign_role_to_user(result["id"], perm_const.Roles.Authenticated.value, perm_const.SCOPE_GLOBAL)

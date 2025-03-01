from __future__ import annotations

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan import types

from ckanext.permissions import const as perm_const
from ckanext.permissions import implementation
from ckanext.permissions import model as perm_model
from ckanext.permissions import types as perm_types
from ckanext.permissions import utils


@tk.blanket.validators
@tk.blanket.actions
@tk.blanket.helpers
@tk.blanket.auth_functions
@tk.blanket.config_declarations
class PermissionsPlugin(implementation.PermissionLabels, p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ISignal)

    _permissions_groups: perm_types.PermissionGroup | None = None
    _permissions = dict[str, perm_types.PermissionDefinition]

    # IConfigurer

    def update_config(self, config_: tk.CKANConfig):
        if not PermissionsPlugin._permissions_groups:  # type: ignore
            PermissionsPlugin._permissions_groups = list(  # type: ignore
                utils.parse_permission_group_schemas().values()
            )
            PermissionsPlugin._permissions = {  # type: ignore
                permission["key"]: permission
                for group in PermissionsPlugin._permissions_groups  # type: ignore
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
        """Assign the default user role to a new user

        Args:
            action_name: The name of the action
            context: The action context
            data_dict: The action payload
            result: The action result
        """
        if action_name != "user_create":
            return

        roles = perm_model.UserRole.get_by_user(result["id"])

        if perm_const.Roles.User.value not in roles:
            perm_model.UserRole.create(result["id"], perm_const.Roles.User.value)

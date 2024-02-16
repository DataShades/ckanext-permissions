from __future__ import annotations

from typing import Any, Optional

import ckan.types as types
import ckan.model as model
import ckan.plugins as p
import ckan.plugins.toolkit as tk

import ckanext.permissions.types as perm_types
import ckanext.permissions.const as perm_const
from ckanext.permissions.interfaces import IPermissions
from ckanext.permissions.model import Permission


def check_access(
    action: str, context: types.Context, data_dict: Optional[dict[str, Any]] = None
) -> bool | None:
    if not is_permission_registered(action):
        return None

    return check_permission(action, context, data_dict)


def is_permission_registered(perm_name: str) -> bool:
    return True


def check_permission(
    perm_name: str, context: types.Context, data_dict: Optional[dict[str, Any]] = None
) -> bool:
    """TODO:
    Check if a given user has a permission to do something. The list of
    Permissions are defined by IPermissions (currently)."""
    userobj = model.User.get(context["user"])

    if not userobj:
        return False

    if userobj.sysadmin:
        return True

    roles = get_permission_roles(perm_name)
    import ipdb

    ipdb.set_trace()


def define_user_role(user: model.User) -> str:
    if user.is_anonymous:
        return perm_const.ROLE_ANON

    if user.sysadmin:
        return perm_const.ROLE_SYSADMIN

    return perm_const.perm_const.ROLE_USER


def get_permission_roles(perm_name: str) -> list[str]:
    return Permission.get_permission_roles(perm_name)


def collect_permission_groups() -> list[perm_types.PermissionGroup]:
    result = []

    for plugin in reversed(list(p.PluginImplementations(IPermissions))):
        result.append(plugin.get_permission_group())

    return result

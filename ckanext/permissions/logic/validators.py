from __future__ import annotations

from typing import Any

import ckan.plugins.toolkit as tk

import ckanext.permissions.const as perm_const
import ckanext.permissions.model as perm_model


def permission_role_is_allowed(role: str) -> str:
    permission_allowed_roles([role])

    return role


def permission_allowed_roles(roles: list[str]) -> Any:
    """Ensures that the tour with a given id exists"""

    for role in roles:
        if role in perm_const.ALLOWED_ROLES:
            continue

        raise tk.Invalid(f"The role {role} is not supported.")

    return roles


def permission_group_exists(group: str) -> str:
    permission_group = perm_model.PermissionGroup.get(group)

    if not permission_group:
        raise tk.Invalid(f"Permission group {group} doesn't exist.")

    return group


def permission_exists(key: str) -> str:
    permission = perm_model.Permission.get(key)

    if not permission:
        raise tk.Invalid(f"Permission {key} doesn't exist.")

    return key

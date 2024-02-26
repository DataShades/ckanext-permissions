from __future__ import annotations

import ckan.plugins.toolkit as tk

import ckanext.permissions.const as perm_const
import ckanext.permissions.model as perm_model


def permission_role_is_allowed(role: str) -> str:
    if role not in perm_const.ALLOWED_ROLES:
        raise tk.Invalid(f"The role {role} is not supported.")

    return role


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

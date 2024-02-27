from __future__ import annotations

from typing import Any, Optional

import ckan.model as model
import ckan.plugins.toolkit as tk
import ckan.types as types

import ckanext.permissions.const as perm_const
import ckanext.permissions.types as perm_types
from ckanext.permissions.model import Permission, PermissionGroup


def check_access(
    action: str, context: types.Context, data_dict: Optional[dict[str, Any]] = None
) -> types.AuthResult | None:
    if not is_permission_registered(action):
        return None

    result = check_permission(action, context, data_dict)

    if result is not None and not result["success"]:  # type: ignore
        raise tk.NotAuthorized(result["msg"])  # type: ignore

    return result


def is_permission_registered(perm_name: str) -> bool:
    return bool(Permission.get(perm_name))


def check_permission(
    perm_name: str, context: types.Context, data_dict: Optional[dict[str, Any]] = None
) -> types.AuthResult | None:
    roles = get_permission_roles(perm_name)
    user_role = define_user_role(context, data_dict)

    for role in roles:
        if role["role"] != user_role:
            continue

        if role["state"] == perm_const.STATE_IGNORE:
            return None

        is_allowed = role["state"] == perm_const.STATE_ALLOW
        return {
            "success": is_allowed,
            "msg": "" if is_allowed else f"Users with role {user_role} are not allowed",
        }

    return {"success": False, "msg": f"Users with role {user_role} are not allowed"}


def define_user_role(
    context: types.Context, data_dict: Optional[dict[str, Any]] = None
) -> str:
    if "user" not in context or not context["user"]:
        return perm_const.ROLE_ANON

    userobj = model.User.get(context["user"])

    if not userobj:
        return perm_const.ROLE_ANON

    if userobj.sysadmin:
        return perm_const.ROLE_SYSADMIN

    return perm_const.ROLE_USER


def get_permission_roles(perm_name: str) -> list[perm_types.PermissionRole]:
    return Permission.get_roles_for_permission(perm_name)


def parse_permission_group_schemas() -> dict[str, perm_types.PermissionGroup]:
    """TODO: now I'm using schema code to safe some time and check if it's
    going to work. We need our implementation for reading perm group schemas"""
    from ckanext.scheming.plugins import _load_schemas

    schema_urls = tk.aslist(tk.config.get("ckanext.permissions.permission_groups"))
    return _load_schemas(schema_urls, "name")


def get_permission_groups() -> list[perm_types.PermissionGroup]:
    from_schemas = parse_permission_group_schemas()
    from_db = [perm_group.dictize({}) for perm_group in PermissionGroup.all()]

    return list(from_schemas.values()) + from_db

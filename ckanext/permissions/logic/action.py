from __future__ import annotations

from typing import cast

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.logic import validate
from ckan.types import Context, DataDict

from ckanext.permissions import model as perm_model
from ckanext.permissions import types as perm_types
from ckanext.permissions import utils as perm_utils
from ckanext.permissions.logic import schema


@validate(schema.role_create)
def permission_role_create(context: Context, data_dict: DataDict) -> perm_types.Role:
    tk.check_access("manage_user_roles", context, data_dict)
    return perm_model.Role.create(**data_dict).dictize(context)


@validate(schema.role_delete)
def permission_role_delete(context: Context, data_dict: DataDict) -> None:
    tk.check_access("manage_user_roles", context, data_dict)

    if role := perm_model.Role.get(data_dict["id"]):
        role.delete()


@validate(schema.role_update)
def permission_role_update(context: Context, data_dict: DataDict) -> perm_types.Role:
    tk.check_access("manage_user_roles", context, data_dict)

    role = cast(perm_model.Role, perm_model.Role.get(data_dict["id"]))

    role.update(data_dict["description"])

    return role.dictize(context)


@validate(schema.permissions_update)
def permissions_update(context: Context, data_dict: DataDict) -> DataDict:
    """Update the permissions for a given permission key.

    Returns:
        A dictionary with the updated permissions and the missing permissions
    """
    tk.check_access("manage_permissions", context, data_dict)

    _validate_permission_data(data_dict)
    registered_permissions = perm_utils.get_permissions()

    updated_permissions = {}
    missing_permissions = []

    for permission_key, roles_data in data_dict["permissions"].items():
        if permission_key not in registered_permissions:
            missing_permissions.append(permission_key)
            continue

        permission_data = {}

        for role_id, flag in roles_data.items():
            role_permission = perm_model.RolePermission.get(role_id, permission_key)

            if flag and role_permission:
                continue

            if not flag and not role_permission:
                continue

            if not flag and role_permission:
                role_permission.delete()
            else:
                perm_model.RolePermission.create(role_id, permission_key)

            permission_data[role_id] = flag

        updated_permissions[permission_key] = permission_data

    model.Session.commit()

    return {
        "updated_permissions": updated_permissions,
        "missing_permissions": missing_permissions,
    }


def _validate_permission_data(data: DataDict) -> None:
    for permission_key, roles_data in data["permissions"].items():
        if not isinstance(permission_key, str):
            raise tk.ValidationError("Invalid permission key")

        if not isinstance(roles_data, dict):
            raise tk.ValidationError("Invalid permission mapping")

        for role_id, flag in roles_data.items():
            if not isinstance(flag, bool):
                raise tk.ValidationError("Invalid permission value")

            data, errors = tk.navl_validate(
                {"id": role_id},
                {
                    "id": [
                        tk.get_validator("not_empty"),
                        tk.get_validator("unicode_safe"),
                        tk.get_validator("permission_role_exists"),
                    ],
                },
            )

            if errors:
                raise tk.ValidationError(errors)

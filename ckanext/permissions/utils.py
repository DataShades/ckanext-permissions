from __future__ import annotations

import inspect
import logging
import os
from typing import cast

import yaml

import ckan.plugins.toolkit as tk
from ckan import model

import ckanext.permissions.const as perm_const
import ckanext.permissions.logic.schema as perm_schema
import ckanext.permissions.model as perm_model
import ckanext.permissions.types as perm_types

log = logging.getLogger(__name__)


def parse_permission_group_schemas() -> dict[str, perm_types.PermissionGroup]:
    groups = _load_schemas(
        tk.aslist(tk.config.get("ckanext.permissions.permission_groups")), "name"
    )

    validate_groups(groups)

    return groups


def _load_schemas(schemas: list[str], type_field: str):
    result = {}

    for path in schemas:
        schema = _load_schema(path)

        if not schema:
            continue

        result[schema[type_field]] = schema

    return result


def _load_schema(path: str):
    """Load permission schema by path.

    Given a path like "ckanext.permissions:default_group.yaml"
    find the second part relative to the import path of the first
    """
    module, file_name = path.split(":", 1)

    try:
        imp_module = __import__(module, fromlist=[""])
    except ImportError:
        return None

    file_path = os.path.join(os.path.dirname(inspect.getfile(imp_module)), file_name)

    if not os.path.exists(file_path):
        return None

    with open(file_path) as file:
        return yaml.safe_load(file)


def validate_groups(groups: dict[str, perm_types.PermissionGroup]) -> bool:
    permissions = []

    for group in groups.values():
        data, errors = tk.navl_validate(
            cast(dict, group), perm_schema.permission_group_schema()
        )

        if errors:
            raise tk.ValidationError(errors)

        if not data.get("permissions"):
            raise tk.ValidationError("Missing permissions")

        if not isinstance(data["permissions"], list):
            raise tk.ValidationError("Permissions must be a list")

        for permission in data["permissions"]:
            if permission["key"] in permissions:
                raise tk.ValidationError(
                    f"Permission {permission['key']} is duplicated"
                )

            permissions.append(permission["key"])

    return True


def get_permission_groups() -> list[perm_types.PermissionGroup]:
    from ckanext.permissions.plugin import PermissionsPlugin # noqa PLC0415

    return PermissionsPlugin._permissions_groups  # type: ignore


def get_permissions() -> dict[str, perm_types.PermissionDefinition]:
    from ckanext.permissions.plugin import PermissionsPlugin # noqa PLC0415

    return PermissionsPlugin._permissions  # type: ignore


def get_registered_roles() -> dict[str, str]:
    return {role["id"]: role["label"] for role in perm_model.Role.all()}


def check_permission(
    permission: str,
    user: model.User | model.AnonymousUser,
    scope: str = "global",
    scope_id: str | None = None,
) -> bool:
    """Check if user has the given permission through any of their roles.

    Args:
        permission: The permission key to check
        user: The user to check permissions for
        scope: The scope of the role
        scope_id: The scope ID of the role, e.g. an organization ID

    Returns:
        bool: True if user has the permission, False otherwise
    """
    if isinstance(user, model.AnonymousUser):
        return (
            perm_model.RolePermission.get(perm_const.Roles.Anonymous.value, permission)
            is not None
        )

    for role in user.roles:  # type: ignore
        if role.scope != scope or role.scope_id != scope_id:
            continue

        if perm_model.RolePermission.get(str(role.role_id), permission) is not None:
            return True

    return False


def assign_role_to_user(
    user_id: str, role_id: str, scope: str = "global", scope_id: str | None = None
):
    """Assign role to an User.

    Args:
        role_id: The role to assign
        user_id: The user to assign the role to
        scope: The scope of the role
        scope_id: The scope ID of the role
    """
    if not perm_model.Role.get(role_id):
        log.warning(
            "Cannot assign role '%s' to user '%s': role does not exist. "
            "Run `ckan permissions init-default-roles` to create default roles.",
            role_id,
            user_id,
        )
        return

    scope_roles = perm_model.UserRole.get(user_id, scope, scope_id)

    if role_id not in [role.role_id for role in scope_roles]:
        perm_model.UserRole.create(user_id, role_id)


def remove_role_from_user(user_id: str, role_id: str):
    """Remove role from an User.

    Args:
        role_id: The role to remove
        user_id: The user to remove the role from
    """
    roles = perm_model.UserRole.get(user_id)

    if role_id in [role.role_id for role in roles]:
        perm_model.UserRole.delete(user_id, role_id)


def ensure_default_roles() -> int:
    """Ensure default roles exist in the database.

    Creates anonymous, authenticated, and administrator roles if they don't exist.

    Returns:
        int: Number of roles created
    """
    default_roles = [
        ("anonymous", "Anonymous", "Default role for anonymous users"),
        (
            "authenticated",
            "Authenticated",
            "Regular user that will be assigned automatically for all users on a portal",
        ),
        (
            "administrator",
            "Administrator",
            "Administrator that should have all permissions",
        ),
    ]

    created_count = 0
    for role_id, label, description in default_roles:
        existing_role = perm_model.Role.get(role_id)
        if not existing_role:
            perm_model.Role.create(role_id, label, description)
            created_count += 1

    return created_count

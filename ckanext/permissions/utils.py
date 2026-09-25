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
    groups = _load_schemas(tk.aslist(tk.config.get("ckanext.permissions.permission_groups")), "name")

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
    dependencies: dict[str, list[str]] = {}
    anonymous: dict[str, bool] = {}

    for group in groups.values():
        data, errors = tk.navl_validate(cast(dict, group), perm_schema.permission_group_schema())

        if errors:
            raise tk.ValidationError(errors)

        if not data.get("permissions"):
            raise tk.ValidationError("Missing permissions")

        if not isinstance(data["permissions"], list):
            raise tk.ValidationError("Permissions must be a list")

        for permission in data["permissions"]:
            if permission["key"] in dependencies:
                raise tk.ValidationError(f"Permission {permission['key']} is duplicated")

            dependencies[permission["key"]] = permission.get("depends_on", [])
            anonymous[permission["key"]] = permission.get("anonymous", True)

    _validate_dependencies(dependencies)
    _validate_anonymous(dependencies, anonymous)

    return True


def _validate_dependencies(dependencies: dict[str, list[str]]) -> None:
    for key, depends_on in dependencies.items():
        for dependency in depends_on:
            if dependency == key:
                raise tk.ValidationError(f"Permission {key} depends on itself")

            if dependency not in dependencies:
                raise tk.ValidationError(f"Permission {key} depends on unknown permission {dependency}")


def _validate_anonymous(dependencies: dict[str, list[str]], anonymous: dict[str, bool]) -> None:
    for key, depends_on in dependencies.items():
        if not anonymous[key]:
            continue

        for dependency in depends_on:
            if not anonymous[dependency]:
                raise tk.ValidationError(
                    f"Permission {key} is allowed for the anonymous role but depends on {dependency}, which is not"
                )


def is_permission_blocked_for_role(permission: str, role_id: str) -> bool:
    """Check if the permission definition forbids giving the permission to the role.

    Args:
        permission: The permission key
        role_id: The role ID

    Returns:
        bool: True for the anonymous role when the definition sets `anonymous: false`
    """
    if role_id != perm_const.Roles.Anonymous.value:
        return False

    definition = get_permissions().get(permission)

    return bool(definition) and not tk.asbool(definition.get("anonymous", True))


def get_permission_dependencies(permission: str) -> list[str]:
    """Get the permissions a role must have before it can be granted this one.

    Args:
        permission: The permission key

    Returns:
        list[str]: The keys of the required permissions
    """
    definition = get_permissions().get(permission)

    return list(definition.get("depends_on", [])) if definition else []


def get_permission_dependents(permission: str) -> list[str]:
    """Get the permissions that require this one.

    Args:
        permission: The permission key

    Returns:
        list[str]: The keys of the dependent permissions
    """
    return [key for key, definition in get_permissions().items() if permission in definition.get("depends_on", [])]


def get_permission_groups() -> list[perm_types.PermissionGroup]:
    from ckanext.permissions.plugin import PermissionsPlugin  # noqa PLC0415

    return PermissionsPlugin._permissions_groups  # type: ignore


def get_permissions() -> dict[str, perm_types.PermissionDefinition]:
    from ckanext.permissions.plugin import PermissionsPlugin  # noqa PLC0415

    return PermissionsPlugin._permissions  # type: ignore


def get_registered_roles() -> dict[str, str]:
    return {role["id"]: role["label"] for role in perm_model.Role.all()}


def check_permission(
    permission: str,
    user: model.User | model.AnonymousUser,
    scope: str = perm_const.SCOPE_GLOBAL,
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
            scope == perm_const.SCOPE_GLOBAL
            and not is_permission_blocked_for_role(permission, perm_const.Roles.Anonymous.value)
            and perm_model.RolePermission.get(perm_const.Roles.Anonymous.value, permission) is not None
        )

    return perm_model.UserRole.has_permission(user.id, permission, scope, scope_id)


def check_package_permission(
    permission: str,
    user: model.User | model.AnonymousUser,
    package: model.Package | None,
) -> bool:
    """Check if user has the given permission globally or in the package's organization.

    Args:
        permission: The permission key to check
        user: The user to check permissions for
        package: The package the permission applies to

    Returns:
        bool: True if user has the permission, False otherwise
    """
    return check_organization_permission(permission, user, package.owner_org if package else None)


def check_organization_permission(
    permission: str,
    user: model.User | model.AnonymousUser,
    organization_id: str | None,
) -> bool:
    """Check if user has the given permission globally or in the organization.

    Args:
        permission: The permission key to check
        user: The user to check permissions for
        organization_id: The ID of the organization the permission applies to

    Returns:
        bool: True if user has the permission, False otherwise
    """
    if check_permission(permission, user):
        return True

    if not organization_id:
        return False

    return check_permission(permission, user, perm_const.SCOPE_ORGANIZATION, organization_id)


def get_permission_scope_ids(
    permissions: list[str],
    user: model.User | model.AnonymousUser,
    scope: str,
) -> set[str]:
    """Get IDs of the scopes where user has any of the given permissions.

    Args:
        permissions: The permission keys to check
        user: The user to check permissions for
        scope: The scope of the roles, e.g. organization

    Returns:
        set[str]: The scope IDs, e.g. organization IDs
    """
    if isinstance(user, model.AnonymousUser):
        return set()

    return perm_model.UserRole.get_scope_ids_with_permissions(user.id, permissions, scope)


def assign_role_to_user(user_id: str, role_id: str, scope: str = perm_const.SCOPE_GLOBAL, scope_id: str | None = None):
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

    perm_model.UserRole.create(user_id, role_id, scope, scope_id)


def remove_role_from_user(
    user_id: str, role_id: str, scope: str = perm_const.SCOPE_GLOBAL, scope_id: str | None = None
):
    """Remove role from an User.

    Args:
        role_id: The role to remove
        user_id: The user to remove the role from
        scope: The scope of the role
        scope_id: The scope ID of the role
    """
    perm_model.UserRole.delete(user_id, role_id, scope, scope_id)


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
            "Role for portal administrators. It has no permissions until they are granted on the permissions page",
        ),
    ]

    created_count = 0
    for role_id, label, description in default_roles:
        existing_role = perm_model.Role.get(role_id)
        if not existing_role:
            perm_model.Role.create(role_id, label, description, commit=False)
            created_count += 1

    model.Session.commit()

    return created_count

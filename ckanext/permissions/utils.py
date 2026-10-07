from __future__ import annotations

import dataclasses
import inspect
import logging
import os
from typing import Any, cast

import yaml

import ckan.plugins.toolkit as tk
from ckan import model

import ckanext.permissions.const as perm_const
import ckanext.permissions.logic.schema as perm_schema
import ckanext.permissions.model as perm_model
import ckanext.permissions.types as perm_types

log = logging.getLogger(__name__)

_reported_unregistered: set[str] = set()


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

    _drop_unknown_dependencies(groups, dependencies)
    _validate_dependencies(dependencies)
    _validate_anonymous(dependencies, anonymous)

    return True


def _drop_unknown_dependencies(
    groups: dict[str, perm_types.PermissionGroup], dependencies: dict[str, list[str]]
) -> None:
    """Drop dependencies on permissions that no loaded group defines.

    A group file removed from the config shouldn't stop CKAN from starting,
    or the `orphans` command couldn't clean up after it.
    """
    for group in groups.values():
        for permission in group["permissions"]:
            depends_on = permission.get("depends_on") or []
            known = [dependency for dependency in depends_on if dependency in dependencies]

            if len(known) == len(depends_on):
                continue

            for dependency in depends_on:
                if dependency not in dependencies:
                    log.warning(
                        "Permission '%s' depends on '%s', which no loaded group defines; ignoring the dependency",
                        permission["key"],
                        dependency,
                    )

            permission["depends_on"] = known
            dependencies[permission["key"]] = known


def _validate_dependencies(dependencies: dict[str, list[str]]) -> None:
    for key, depends_on in dependencies.items():
        if key in depends_on:
            raise tk.ValidationError(f"Permission {key} depends on itself")


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


def parse_declared_roles() -> dict[str, perm_types.RoleDefinition]:
    """Load the roles declared via ckanext.permissions.roles, keyed by id."""
    roles = _load_role_schemas(tk.aslist(tk.config.get("ckanext.permissions.roles")))

    validate_roles(roles)

    return roles


def _load_role_schemas(paths: list[str]) -> dict[str, perm_types.RoleDefinition]:
    result: dict[str, perm_types.RoleDefinition] = {}

    for path in paths:
        schema = _load_schema(path)

        if not schema:
            continue

        for role in schema.get("roles") or []:
            role_id = role.get("id")

            if role_id in result:
                log.warning(
                    "Role '%s' is declared more than once; keeping the first declaration and ignoring '%s'",
                    role_id,
                    path,
                )
                continue

            result[role_id] = role

    return result


def validate_roles(roles: dict[str, perm_types.RoleDefinition]) -> bool:
    for role in roles.values():
        data, errors = tk.navl_validate(cast(dict, role), perm_schema.role_definition_schema())

        if errors:
            raise tk.ValidationError(errors)

    return True


def get_declared_roles() -> dict[str, perm_types.RoleDefinition]:
    from ckanext.permissions.plugin import PermissionsPlugin  # noqa PLC0415

    return PermissionsPlugin._declared_roles  # type: ignore


def check_permission(
    permission: str,
    user: model.User | model.AnonymousUser,
    scope: str | None = None,
    scope_id: str | None = None,
) -> bool:
    """Check if user has the given permission globally or through a role in the scope.

    The implicit roles aren't assigned: the grants of the anonymous role apply
    to every user, logged in or not, and those of the authenticated role to
    every logged-in user. Both count as global.

    Args:
        permission: The permission key to check
        user: The user to check permissions for
        scope: The scope of the roles, e.g. organization. Without it, or
            without scope_id, only global roles are checked
        scope_id: The scope ID, e.g. an organization ID

    Returns:
        bool: True if user has the permission, False otherwise
    """
    if not _is_registered(permission):
        return False

    if _implicit_roles_have_permission(permission, user):
        return True

    if isinstance(user, model.AnonymousUser):
        return False

    if perm_model.UserRole.has_permission(user.id, permission):
        return True

    if not (scope and scope_id):
        return False

    return perm_model.UserRole.has_permission(user.id, permission, scope, scope_id)


def _is_registered(permission: str) -> bool:
    """Check that a loaded permission group defines the permission.

    Grants of permissions that are no longer defined stay in the database but
    have no effect, because the permissions page can't show or revoke them.
    """
    if permission in get_permissions():
        return True

    if permission not in _reported_unregistered:
        _reported_unregistered.add(permission)
        log.warning(
            "Permission '%s' is not defined by any group in ckanext.permissions.permission_groups, "
            "so it is never granted",
            permission,
        )

    return False


def get_unregistered_grants() -> list[perm_model.RolePermission]:
    """Get the role grants of permissions that no loaded permission group defines."""
    return perm_model.RolePermission.get_unregistered(list(get_permissions()))


def export_permissions() -> perm_types.PermissionsExport:
    """Get the permissions of every role, in the format `plan_permissions_import` reads.

    Grants of permissions that no loaded group defines are left out.
    """
    registered = get_permissions()
    roles = {}

    for role_id in get_registered_roles():
        granted = perm_model.RolePermission.get_for_role(role_id)
        roles[role_id] = [permission for permission in granted if permission in registered]

    return {"version": perm_const.EXPORT_VERSION, "roles": roles}


@dataclasses.dataclass
class PermissionsImport:
    """Permissions to apply from an export of another portal.

    Attributes:
        permissions: The `permissions_update` payload. Every role of the export
            that exists here gets exactly the permissions listed for it.
        unknown_roles: Roles of the export that don't exist here
        unknown_permissions: Permissions of the export that no loaded group defines
        blocked: `(permission, role)` grants of the export the role can't be given
    """

    permissions: dict[str, dict[str, bool]]
    unknown_roles: list[str]
    unknown_permissions: list[str]
    blocked: list[tuple[str, str]]

    def get_changes(self) -> list[tuple[str, str, bool]]:
        """Get the `(permission, role, granted)` grants that differ from the current ones."""
        current: dict[str, set[str]] = {}
        changes = []

        for permission, roles in self.permissions.items():
            for role_id, granted in roles.items():
                if role_id not in current:
                    current[role_id] = set(perm_model.RolePermission.get_for_role(role_id))

                if granted != (permission in current[role_id]):
                    changes.append((permission, role_id, granted))

        return changes


def plan_permissions_import(data: Any) -> PermissionsImport:
    """Match an export of another portal against the roles and permissions of this one.

    Args:
        data: The output of `export_permissions`

    Raises:
        tk.ValidationError: The data isn't an export this version can read
    """
    _validate_export(data)

    registered = get_permissions()
    roles = get_registered_roles()
    result = PermissionsImport({key: {} for key in registered}, [], [], [])
    unknown_permissions: set[str] = set()

    for role_id, granted in data["roles"].items():
        unknown_permissions.update(permission for permission in granted if permission not in registered)

        if role_id not in roles:
            result.unknown_roles.append(role_id)
            continue

        for permission in registered:
            flag = permission in granted

            if flag and is_permission_blocked_for_role(permission, role_id):
                result.blocked.append((permission, role_id))
                flag = False

            result.permissions[permission][role_id] = flag

    result.unknown_permissions = sorted(unknown_permissions)

    return result


def _validate_export(data: Any) -> None:
    if not isinstance(data, dict):
        raise tk.ValidationError(tk._("The export must be a JSON object"))

    if data.get("version") != perm_const.EXPORT_VERSION:
        raise tk.ValidationError(
            tk._("Unsupported export version {version}, expected {expected}").format(
                version=data.get("version"), expected=perm_const.EXPORT_VERSION
            )
        )

    roles = data.get("roles")

    if not isinstance(roles, dict) or not all(
        isinstance(granted, list) and all(isinstance(permission, str) for permission in granted)
        for granted in roles.values()
    ):
        raise tk.ValidationError(tk._("The export must map each role to a list of permissions"))


@dataclasses.dataclass
class RoleDrift:
    """A declared role whose label or description differs from the database."""

    role_id: str
    field: str
    declared: str
    current: str


@dataclasses.dataclass
class UndeclaredRole:
    """A database role no longer declared by any loaded roles file."""

    role_id: str
    label: str
    user_count: int
    permission_count: int


@dataclasses.dataclass
class RolesSyncPlan:
    """Declared roles (ckanext.permissions.roles) matched against the database.

    Attributes:
        to_create: Declared roles missing from the database
        drifted: Declared roles whose label/description differs from the database
        undeclared: Database roles no longer declared anywhere, with usage counts
    """

    to_create: list[perm_types.RoleDefinition]
    drifted: list[RoleDrift]
    undeclared: list[UndeclaredRole]


def plan_roles_sync() -> RolesSyncPlan:
    """Match the declared roles against the database.

    The 3 implicit/default roles (`perm_const.Roles`) are never reported as
    undeclared: they aren't meant to be declared through this mechanism, they
    are seeded by a migration instead, so flagging them here would be a
    permanent, unfixable warning on every portal.
    """
    declared = get_declared_roles()
    existing = {role["id"]: role for role in perm_model.Role.all()}

    to_create = [role for role_id, role in declared.items() if role_id not in existing]

    drifted: list[RoleDrift] = []

    for role_id, role in declared.items():
        current = existing.get(role_id)

        if not current:
            continue

        if current["label"] != role["label"]:
            drifted.append(RoleDrift(role_id, "label", role["label"], current["label"]))

        if current["description"] != role["description"]:
            drifted.append(RoleDrift(role_id, "description", role["description"], current["description"]))

    implicit_and_default = {role.value for role in perm_const.Roles}
    undeclared_ids = sorted(set(existing) - set(declared) - implicit_and_default)
    undeclared = [
        UndeclaredRole(
            role_id,
            existing[role_id]["label"],
            user_count=perm_model.UserRole.count_for_role(role_id),
            permission_count=len(perm_model.RolePermission.get_for_role(role_id)),
        )
        for role_id in undeclared_ids
    ]

    return RolesSyncPlan(to_create, drifted, undeclared)


def _implicit_roles_have_permission(permission: str, user: model.User | model.AnonymousUser) -> bool:
    anonymous = perm_const.Roles.Anonymous.value
    roles = [] if is_permission_blocked_for_role(permission, anonymous) else [anonymous]

    if not isinstance(user, model.AnonymousUser):
        roles.append(perm_const.Roles.Authenticated.value)

    return bool(roles) and perm_model.RolePermission.is_granted_to_any(roles, permission)


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
    permissions = [permission for permission in permissions if _is_registered(permission)]

    if isinstance(user, model.AnonymousUser) or not permissions:
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
            "Run `ckan db upgrade -p permissions` to create the default roles.",
            role_id,
            user_id,
        )
        return

    perm_model.UserRole.create(user_id, role_id, scope, scope_id)

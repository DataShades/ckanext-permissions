from __future__ import annotations

import logging
from typing import cast

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.lib.dictization import model_dictize
from ckan.logic import validate
from ckan.types import Action, Context, DataDict

from ckanext.permissions import const as perm_const
from ckanext.permissions import model as perm_model
from ckanext.permissions import types as perm_types
from ckanext.permissions import utils as perm_utils
from ckanext.permissions.logic import schema

log = logging.getLogger(__name__)


@validate(schema.role_create)
def permission_role_create(context: Context, data_dict: DataDict) -> perm_types.Role:
    tk.check_access("manage_user_roles", context, data_dict)

    role = perm_model.Role.create(**data_dict)
    log.info("Role created: role=%s actor=%s", role.id, context.get("user"))

    return role.dictize(context)


@validate(schema.role_delete)
def permission_role_delete(context: Context, data_dict: DataDict) -> None:
    tk.check_access("manage_user_roles", context, data_dict)

    if role := perm_model.Role.get(data_dict["id"]):
        role.delete()
        log.info("Role deleted: role=%s actor=%s", data_dict["id"], context.get("user"))


@validate(schema.role_update)
def permission_role_update(context: Context, data_dict: DataDict) -> perm_types.Role:
    tk.check_access("manage_user_roles", context, data_dict)

    role = cast(perm_model.Role, perm_model.Role.get(data_dict["id"]))

    old_label, old_description = role.label, role.description
    role.update(data_dict["description"], data_dict.get("label"))

    log.info(
        "Role updated: role=%s label=%r -> %r description=%r -> %r actor=%s",
        role.id,
        old_label,
        role.label,
        old_description,
        role.description,
        context.get("user"),
    )

    return role.dictize(context)


@validate(schema.permissions_update)
def permissions_update(context: Context, data_dict: DataDict) -> DataDict:
    """Update the permissions for a given permission key.

    Returns:
        A dictionary with the updated permissions and the missing permissions
    """
    tk.check_access("manage_permissions", context, data_dict)

    _validate_permission_data(data_dict)

    if errors := _check_blocked_roles(data_dict["permissions"]):
        raise tk.ValidationError(errors)

    registered_permissions = perm_utils.get_permissions()

    updated_permissions = {}
    missing_permissions = []

    for permission_key, roles_data in data_dict["permissions"].items():
        if permission_key not in registered_permissions:
            missing_permissions.append(permission_key)
            continue

        updated_permissions[permission_key] = _update_role_permissions(permission_key, roles_data)

    model.Session.flush()

    if errors := _check_dependencies(updated_permissions):
        model.Session.rollback()
        raise tk.ValidationError(errors)

    model.Session.commit()

    for permission_key, permission_data in updated_permissions.items():
        for role_id, flag in permission_data.items():
            log.info(
                "Permission %s: permission=%s role=%s actor=%s",
                "granted" if flag else "revoked",
                permission_key,
                role_id,
                context.get("user"),
            )

    return {
        "updated_permissions": updated_permissions,
        "missing_permissions": missing_permissions,
    }


def _update_role_permissions(permission_key: str, roles_data: dict[str, bool]) -> dict[str, bool]:
    """Grant or revoke the permission for each role, without committing.

    Returns:
        The roles whose permission changed, mapped to the new value
    """
    changed = {}

    for role_id, flag in roles_data.items():
        role_permission = perm_model.RolePermission.get(role_id, permission_key)

        if bool(role_permission) == flag:
            continue

        if role_permission:
            role_permission.delete(commit=False)
        else:
            perm_model.RolePermission.create(role_id, permission_key, commit=False)

        changed[role_id] = flag

    return changed


def _check_blocked_roles(permissions: dict[str, dict[str, bool]]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}

    for permission_key, roles_data in permissions.items():
        for role_id, granted in roles_data.items():
            if granted and perm_utils.is_permission_blocked_for_role(permission_key, role_id):
                errors.setdefault(permission_key, []).append(
                    tk._("Permission can't be given to the {role} role").format(role=role_id)
                )

    return errors


def _check_dependencies(updated_permissions: dict[str, dict[str, bool]]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}

    for permission_key, roles_data in updated_permissions.items():
        for role_id, granted in roles_data.items():
            if granted:
                missing = [
                    dependency
                    for dependency in perm_utils.get_permission_dependencies(permission_key)
                    if not perm_model.RolePermission.get(role_id, dependency)
                ]
                if missing:
                    errors.setdefault(permission_key, []).append(
                        tk._("Role {role} also needs: {permissions}").format(
                            role=role_id, permissions=", ".join(missing)
                        )
                    )
            else:
                dependents = [
                    dependent
                    for dependent in perm_utils.get_permission_dependents(permission_key)
                    if perm_model.RolePermission.get(role_id, dependent)
                ]
                if dependents:
                    errors.setdefault(permission_key, []).append(
                        tk._("Role {role} still has permissions that depend on it: {permissions}").format(
                            role=role_id, permissions=", ".join(dependents)
                        )
                    )

    return errors


def _validate_permission_data(data: DataDict) -> None:
    for permission_key, roles_data in data["permissions"].items():
        if not isinstance(permission_key, str):
            raise tk.ValidationError(tk._("Invalid permission key"))

        if not isinstance(roles_data, dict):
            raise tk.ValidationError(tk._("Invalid permission mapping"))

        for role_id, flag in roles_data.items():
            if not isinstance(flag, bool):
                raise tk.ValidationError(tk._("Invalid permission value"))

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


@tk.chained_action
def organization_list_for_user(next_: Action, context: Context, data_dict: DataDict) -> list[DataDict]:
    """Add the organizations where the user can create datasets through the `create_dataset` permission.

    The dataset form picks its organizations from this action.
    """
    organizations = next_(context, data_dict)

    if data_dict.get("permission") != "create_dataset":
        return organizations

    user = model.User.get(data_dict.get("id") or context.get("user"))

    if not user or user.sysadmin:
        return organizations

    query = model.Session.query(model.Group).filter(
        model.Group.is_organization == True,
        model.Group.state == model.State.ACTIVE,
        model.Group.id.notin_([organization["id"] for organization in organizations]),
    )

    if not perm_utils.check_permission("create_dataset", user):
        scope_ids = perm_utils.get_permission_scope_ids(["create_dataset"], user, perm_const.SCOPE_ORGANIZATION)
        query = query.filter(model.Group.id.in_(scope_ids))

    extra = model_dictize.group_list_dictize(
        query.all(),
        Context(context, with_capacity=False),
        with_package_counts=tk.asbool(data_dict.get("include_dataset_count")),
        with_member_counts=tk.asbool(data_dict.get("include_member_count")),
    )

    return sorted([*organizations, *extra], key=lambda organization: tk.h.strxfrm(organization["display_name"]))


@tk.chained_action
def group_list_authz(next_: Action, context: Context, data_dict: DataDict) -> list[DataDict]:
    """List every group for users with the `manage_any_group` permission, as core does for sysadmins.

    The dataset's Groups page picks its groups from this action.
    """
    user = model.User.get(context.get("user"))

    if (
        not user
        or user.sysadmin
        or tk.asbool(data_dict.get("am_member"))
        or not perm_utils.check_permission("manage_any_group", user)
    ):
        return next_(context, data_dict)

    tk.check_access("group_list_authz", context, data_dict)

    groups = (
        model.Session.query(model.Group)
        .filter(model.Group.is_organization == False, model.Group.state == model.State.ACTIVE)
        .all()
    )

    package = context.get("package")

    if tk.asbool(data_dict.get("available_only")) and package:
        groups = list(set(groups) - set(package.get_groups()))

    return model_dictize.group_list_dictize(
        groups,
        context,
        with_package_counts=tk.asbool(data_dict.get("include_dataset_count")),
        with_member_counts=tk.asbool(data_dict.get("include_member_count")),
    )

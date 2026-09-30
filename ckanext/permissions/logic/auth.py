from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import ckan.plugins.toolkit as tk
from ckan import authz, model, types
from ckan.logic.auth.create import _check_group_auth

import ckanext.permissions.const as perm_const
import ckanext.permissions.utils as perm_utils

_SUPPRESSED_PERMISSIONS = "permissions_suppressed"


def _chained_auth(*, allow_anonymous: bool) -> Callable[[types.ChainedAuthFunction], types.ChainedAuthFunction]:
    """Chain an auth function and set its anonymous access flag explicitly.

    CKAN copies only the outermost chained function's flags onto the whole
    chain, so this flag replaces the one of the core auth function.
    """
    set_anonymous_access = tk.auth_allow_anonymous_access if allow_anonymous else tk.auth_disallow_anonymous_access

    def decorator(func: types.ChainedAuthFunction) -> types.ChainedAuthFunction:
        return set_anonymous_access(tk.chained_auth_function(func))

    return decorator


def _get_user(context: types.Context) -> model.User | model.AnonymousUser:
    return model.User.get(context.get("user")) or model.AnonymousUser()


def _get_suppressed(context: types.Context) -> frozenset[str]:
    return cast("dict[str, Any]", context).get(_SUPPRESSED_PERMISSIONS, frozenset())


def _suppress(context: types.Context, *permissions: str) -> types.Context:
    """Copy the context for core auth, so it can't reach our grants for these permissions.

    Core `package_delete` auth defers to `package_update`, and `resource_delete`
    to `package_delete`. Without this, `update_any_dataset` would also allow
    deleting datasets and resources.
    """
    return cast(types.Context, {**context, _SUPPRESSED_PERMISSIONS: _get_suppressed(context) | set(permissions)})


def _check_package_permission(permission: str, context: types.Context, package: model.Package | None) -> bool:
    if permission in _get_suppressed(context):
        return False

    return _check_organization_permission(permission, _get_user(context), package.owner_org if package else None)


def _check_organization_permission(
    permission: str, user: model.User | model.AnonymousUser, organization_id: str | None
) -> bool:
    return perm_utils.check_permission(permission, user, perm_const.SCOPE_ORGANIZATION, organization_id)


def _get_package(data_dict: types.DataDict | None) -> model.Package | None:
    package_id = (data_dict or {}).get("id")

    return model.Package.get(package_id) if package_id else None


def _get_resource_package(data_dict: types.DataDict | None) -> model.Package | None:
    resource_id = (data_dict or {}).get("id")
    resource = model.Resource.get(resource_id) if resource_id else None

    return model.Package.get(resource.package_id) if resource else None


def _get_group(data_dict: types.DataDict | None) -> model.Group | None:
    group_id = (data_dict or {}).get("id")

    return model.Group.get(group_id) if group_id else None


def _get_organization_id(organization_id: str | None) -> str | None:
    organization = model.Group.get(organization_id) if organization_id else None

    return organization.id if organization and organization.is_organization else None


def _can_manage_organization_member(
    user: model.User | model.AnonymousUser, organization: model.Group, data_dict: types.DataDict
) -> bool:
    if not _check_organization_permission("manage_organization_members", user, organization.id):
        return False

    target_name = data_dict.get("object") or data_dict.get("username")

    if not target_name:
        return True

    target = model.User.get(target_name)
    role = data_dict.get("capacity") or data_dict.get("role")

    return bool(
        target
        and target.id != getattr(user, "id", None)
        and role != "admin"
        and authz.users_role_for_group_or_org(organization.id, target.name) != "admin"
    )


@_chained_auth(allow_anonymous=True)
def package_create(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    user = _get_user(context)
    owner_org = (data_dict or {}).get("owner_org")

    if owner_org:
        allowed = _check_organization_permission("create_dataset", user, _get_organization_id(owner_org))
    else:
        allowed = perm_utils.check_permission("create_dataset", user) or bool(
            perm_utils.get_permission_scope_ids(["create_dataset"], user, perm_const.SCOPE_ORGANIZATION)
        )

    if allowed and _check_group_auth(context, data_dict or {}):
        return {"success": True}

    return next_(context, data_dict or {})


@_chained_auth(allow_anonymous=True)
def package_show(
    next_: types.AuthFunction,
    context: types.Context,
    data_dict: types.DataDict | None,
) -> types.AuthResult:
    user = _get_user(context)
    package = context.get("package")  # type: ignore

    if not package:
        return next_(context, data_dict or {})

    # Check permissions in order of precedence
    permission_checks = [
        ("read_any_dataset", None),
        ("read_private_dataset", lambda: package.private),
    ]

    for permission, condition in permission_checks:
        if condition is not None and not condition():
            continue

        if _check_organization_permission(permission, user, package.owner_org):
            return {"success": True}

    return next_(context, data_dict or {})


@_chained_auth(allow_anonymous=True)
def package_update(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    if _check_package_permission("update_any_dataset", context, _get_package(data_dict)):
        return {"success": True}

    return next_(context, data_dict or {})


@_chained_auth(allow_anonymous=False)
def package_delete(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    if _check_package_permission("delete_any_dataset", context, _get_package(data_dict)):
        return {"success": True}

    return next_(_suppress(context, "update_any_dataset"), data_dict or {})


@_chained_auth(allow_anonymous=False)
def resource_delete(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    if _check_package_permission("delete_any_resource", context, _get_resource_package(data_dict)):
        return {"success": True}

    return next_(_suppress(context, "update_any_dataset", "delete_any_dataset"), data_dict or {})


@_chained_auth(allow_anonymous=False)
def dataset_purge(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    if _check_package_permission("purge_dataset", context, _get_package(data_dict)):
        return {"success": True}

    return next_(context, data_dict or {})


def _manage_collaborators(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    if _check_package_permission("manage_dataset_collaborators", context, _get_package(data_dict)):
        return {"success": True}

    return next_(context, data_dict or {})


@_chained_auth(allow_anonymous=False)
def package_collaborator_create(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    user = _get_user(context)
    target = model.User.get((data_dict or {}).get("user_id") or "")

    if target and target.id == getattr(user, "id", None):
        return next_(context, data_dict or {})

    return _manage_collaborators(next_, context, data_dict)


@_chained_auth(allow_anonymous=False)
def package_collaborator_delete(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    return _manage_collaborators(next_, context, data_dict)


# Core allows anonymous access here, then fails on an assertion for anonymous users.
@_chained_auth(allow_anonymous=False)
def package_collaborator_list(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    return _manage_collaborators(next_, context, data_dict)


def _bulk_update(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    organization_id = _get_organization_id((data_dict or {}).get("org_id"))

    if _check_organization_permission("bulk_update_datasets", _get_user(context), organization_id):
        return {"success": True}

    return next_(context, data_dict or {})


@_chained_auth(allow_anonymous=False)
def bulk_update_private(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    return _bulk_update(next_, context, data_dict)


@_chained_auth(allow_anonymous=False)
def bulk_update_public(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    return _bulk_update(next_, context, data_dict)


@_chained_auth(allow_anonymous=False)
def bulk_update_delete(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    return _bulk_update(next_, context, data_dict)


@_chained_auth(allow_anonymous=False)
def organization_create(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    if perm_utils.check_permission("create_organization", _get_user(context)):
        return {"success": True}

    return next_(context, data_dict or {})


@_chained_auth(allow_anonymous=False)
def group_create(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    if perm_utils.check_permission("create_group", _get_user(context)):
        return {"success": True}

    return next_(context, data_dict or {})


def _can_manage_group(user: model.User | model.AnonymousUser, group: model.Group | None) -> bool:
    return bool(group and not group.is_organization and perm_utils.check_permission("manage_any_group", user))


@_chained_auth(allow_anonymous=False)
def group_update(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    if _can_manage_group(_get_user(context), _get_group(data_dict)):
        return {"success": True}

    return next_(context, data_dict or {})


@_chained_auth(allow_anonymous=False)
def group_member_create(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    if _can_manage_group(_get_user(context), _get_group(data_dict)):
        return {"success": True}

    return next_(context, data_dict or {})


@_chained_auth(allow_anonymous=False)
def organization_member_create(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    organization = _get_group(data_dict)

    if organization and _can_manage_organization_member(_get_user(context), organization, data_dict or {}):
        return {"success": True}

    return next_(context, data_dict or {})


@_chained_auth(allow_anonymous=False)
def group_edit_permissions(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    user = _get_user(context)
    group = _get_group(data_dict)

    if _can_manage_group(user, group) or (
        group
        and group.is_organization
        and _check_organization_permission("manage_organization_members", user, group.id)
    ):
        return {"success": True}

    return next_(context, data_dict or {})


@_chained_auth(allow_anonymous=False)
def member_create(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    """Grant member changes through `manage_any_group` or `manage_organization_members`.

    `member_delete` delegates to this function, so it covers removing members too.
    """
    user = _get_user(context)
    group = _get_group(data_dict)

    if _can_manage_group(user, group) or (
        group
        and group.is_organization
        and (data_dict or {}).get("object_type") == "user"
        and _can_manage_organization_member(user, group, data_dict or {})
    ):
        return {"success": True}

    return next_(context, data_dict or {})


def manage_user_roles(context: types.Context, data_dict: types.DataDict) -> types.AuthResult:
    return {"success": False}


def manage_permissions(context: types.Context, data_dict: types.DataDict) -> types.AuthResult:
    return {"success": False}

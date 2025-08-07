from __future__ import annotations

import ckan.plugins.toolkit as tk
from ckan import model, types

import ckanext.permissions.utils as perm_utils


@tk.chained_auth_function
@tk.auth_allow_anonymous_access
def package_show(
    next_: types.AuthFunction,
    context: types.Context,
    data_dict: types.DataDict | None,
) -> types.AuthResult:
    user = model.User.get(context.get("user")) or model.AnonymousUser()
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

        if perm_utils.check_permission(permission, user):
            return {"success": True}

    return next_(context, data_dict or {})


@tk.chained_auth_function
@tk.auth_allow_anonymous_access
def package_update(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    user = model.User.get(context.get("user")) or model.AnonymousUser()

    if perm_utils.check_permission("update_any_dataset", user):
        return {"success": True}

    return next_(context, data_dict or {})


@tk.chained_auth_function
@tk.auth_allow_anonymous_access
def package_delete(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    user = model.User.get(context.get("user")) or model.AnonymousUser()

    if perm_utils.check_permission("delete_any_dataset", user):
        return {"success": True}

    return next_(context, data_dict or {})


@tk.chained_auth_function
@tk.auth_allow_anonymous_access
def resource_delete(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    user = model.User.get(context.get("user")) or model.AnonymousUser()

    if perm_utils.check_permission("delete_any_resource", user):
        return {"success": True}

    return next_(context, data_dict or {})


def manage_user_roles(context: types.Context, data_dict: types.DataDict) -> types.AuthResult:
    return {"success": False}


def manage_permissions(context: types.Context, data_dict: types.DataDict) -> types.AuthResult:
    return {"success": False}

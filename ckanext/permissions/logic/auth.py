from __future__ import annotations

import ckan.plugins.toolkit as tk
from ckan import model, types

import ckanext.permissions.utils as perm_utils


def _get_user(context: types.Context) -> model.User | model.AnonymousUser:
    return model.User.get(context.get("user")) or model.AnonymousUser()


def _get_package(data_dict: types.DataDict | None) -> model.Package | None:
    package_id = (data_dict or {}).get("id")

    return model.Package.get(package_id) if package_id else None


def _get_resource_package(data_dict: types.DataDict | None) -> model.Package | None:
    resource_id = (data_dict or {}).get("id")
    resource = model.Resource.get(resource_id) if resource_id else None

    return model.Package.get(resource.package_id) if resource else None


@tk.chained_auth_function
@tk.auth_allow_anonymous_access
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

        if perm_utils.check_package_permission(permission, user, package):
            return {"success": True}

    return next_(context, data_dict or {})


@tk.chained_auth_function
@tk.auth_allow_anonymous_access
def package_update(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    if perm_utils.check_package_permission("update_any_dataset", _get_user(context), _get_package(data_dict)):
        return {"success": True}

    return next_(context, data_dict or {})


@tk.chained_auth_function
@tk.auth_allow_anonymous_access
def package_delete(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    if perm_utils.check_package_permission("delete_any_dataset", _get_user(context), _get_package(data_dict)):
        return {"success": True}

    return next_(context, data_dict or {})


@tk.chained_auth_function
@tk.auth_allow_anonymous_access
def resource_delete(
    next_: types.AuthFunction, context: types.Context, data_dict: types.DataDict | None
) -> types.AuthResult:
    if perm_utils.check_package_permission("delete_any_resource", _get_user(context), _get_resource_package(data_dict)):
        return {"success": True}

    return next_(context, data_dict or {})


def manage_user_roles(context: types.Context, data_dict: types.DataDict) -> types.AuthResult:
    return {"success": False}


def manage_permissions(context: types.Context, data_dict: types.DataDict) -> types.AuthResult:
    return {"success": False}

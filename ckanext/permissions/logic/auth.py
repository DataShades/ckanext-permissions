from __future__ import annotations

import ckan.plugins.toolkit as tk
from ckan import model, types

import ckanext.permissions.utils as perm_utils


@tk.chained_auth_function
def package_show(
    next_: types.AuthFunction,
    context: types.Context,
    data_dict: types.DataDict | None,
) -> types.AuthResult:
    user = model.User.get(context.get("user")) or model.AnonymousUser()
    package = context.get("package")  # type: ignore

    if not user or not package:
        return next_(context, data_dict or {})

    # Check permissions in order of precedence
    permission_checks = [
        ("read_any_dataset", None),
        ("read_private_dataset", lambda: package.private),
        ("read_own_dataset", lambda: user.id == package.creator_user_id),
        ("read_own_private_dataset", lambda: user.id == package.creator_user_id),
    ]

    for permission, condition in permission_checks:
        if condition is not None and not condition():
            continue

        if perm_utils.check_permission(permission, user):
            return {"success": True}

    return next_(context, data_dict or {})

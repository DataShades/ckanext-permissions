from __future__ import annotations

from typing import Any

import ckan.plugins.toolkit as tk

import ckanext.permissions.const as perm_const


def permission_allowed_roles(roles: list[str]) -> Any:
    """Ensures that the tour with a given id exists"""

    for role in roles:
        if role in perm_const.ALLOWED_ROLES:
            continue

        raise tk.Invalid(f"The role {role} is not supported.")

    return roles

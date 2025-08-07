from __future__ import annotations

import re

import ckan.plugins.toolkit as tk

import ckanext.permissions.const as perm_const
import ckanext.permissions.model as perm_model


def role_doesnt_exists(role: str) -> str:
    """Ensure that a role doesn't exists.

    Args:
        role (str): role name

    Raises:
        tk.Invalid: if the role exists

    Returns:
        role name
    """
    if perm_model.Role.get(role) is not None:
        raise tk.Invalid(f"Role {role} is already exists")

    return role


def permission_role_exists(role: str) -> str:
    """Ensure that a role exists.

    Args:
        role (str): role name

    Raises:
        tk.Invalid: if the role doesn't exists

    Returns:
        role name
    """
    if perm_model.Role.get(role) is None:
        raise tk.Invalid(f"Role {role} doesn't exists")

    return role


def roles_exists(roles: list[str]) -> list[str]:
    """Ensure that all roles exists.

    Args:
        roles (list[str]): list of roles

    Raises:
        tk.Invalid: if a role doesn't exists

    Returns:
        list of roles
    """
    for role in roles:
        permission_role_exists(role)

    return roles


def role_id_validator(value: str) -> str:
    """Validate a role ID.

    Ensures that:
        - the role ID is a string
        - is at least N characters long
        - is at most N characters long
        - contains only lowercase alpha (ascii) characters and these symbols: -_

    Args:
        value (str): role ID

    Raises:
        tk.Invalid: if the role ID is invalid

    Returns:
        role ID
    """
    name_match = re.compile(r"[a-z_\-]*$")

    if len(value) < perm_const.ROLE_ID_MIN_LENGTH:
        raise tk.Invalid(f"Role ID must be at least {perm_const.ROLE_ID_MIN_LENGTH} characters long.")

    if len(value) > perm_const.ROLE_ID_MAX_LENGTH:
        raise tk.Invalid(f"Role ID must be a maximum of {perm_const.ROLE_ID_MAX_LENGTH} characters long.")

    if not name_match.match(value):
        raise tk.Invalid("Role ID must be purely lowercase alpha(ascii) characters and these symbols: -_")

    return value


def not_default_role(role_id: str) -> str:
    """Ensure that the role is not a default role.

    Args:
        role_id (str): role ID

    Raises:
        tk.Invalid: if the role is a default role

    Returns:
        role ID
    """
    if role_id in [role.value for role in perm_const.Roles]:
        raise tk.Invalid(f"Role {role_id} is a default role.")

    return role_id

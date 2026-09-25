from __future__ import annotations

import re
from typing import Any

import ckan.plugins.toolkit as tk
from ckan import model, types
from ckan.logic import validators as core_validators

import ckanext.permissions.const as perm_const
import ckanext.permissions.model as perm_model
import ckanext.permissions.utils as perm_utils


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
        raise tk.Invalid(tk._("Role {role} already exists").format(role=role))

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
        raise tk.Invalid(tk._("Role {role} doesn't exist").format(role=role))

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
    if len(value) < perm_const.ROLE_ID_MIN_LENGTH:
        raise tk.Invalid(
            tk._("Role ID must be at least {min} characters long.").format(min=perm_const.ROLE_ID_MIN_LENGTH)
        )

    if len(value) > perm_const.ROLE_ID_MAX_LENGTH:
        raise tk.Invalid(
            tk._("Role ID must be at most {max} characters long.").format(max=perm_const.ROLE_ID_MAX_LENGTH)
        )

    if not re.fullmatch(perm_const.ROLE_ID_PATTERN, value):
        raise tk.Invalid(tk._('Role ID can only contain lowercase letters (a-z), "-" and "_".'))

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
        raise tk.Invalid(tk._("Role {role} is a default role.").format(role=role_id))

    return role_id


def owner_org_validator(
    key: types.FlattenKey, data: types.FlattenDataDict, errors: types.FlattenErrorDict, context: types.Context
) -> Any:
    """Allow the `create_dataset` permission to pick the dataset's organization.

    Core checks the organization membership directly instead of `package_create` auth,
    so the permission has to be honored here too.
    """
    value = data.get(key)
    organization = model.Group.get(value) if isinstance(value, str) and value else None

    if organization and organization.is_organization and not context.get("ignore_auth"):
        user = model.User.get(context.get("user")) or model.AnonymousUser()

        if perm_utils.check_organization_permission("create_dataset", user, organization.id):
            context = types.Context(context, ignore_auth=True)

    return core_validators.owner_org_validator(key, data, errors, context)

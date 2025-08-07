from __future__ import annotations

from ckanext.permissions import const, model, utils


def get_registered_roles() -> dict[str, str]:
    """Get the registered roles

    Returns:
        The registered roles
    """
    return utils.get_registered_roles()


def get_role_permissions(role_id: str, permission: str) -> bool:
    """Check if a role has a permission

    Args:
        role_id (str): The id of the role
        permission (str): The permission to check

    Returns:
        True if the role has the permission, False otherwise
    """
    return model.RolePermission.get(role_id, permission) is not None


def get_user_roles(user_id: str, scope: str = "global", scope_id: str | None = None) -> list[str]:
    """Get the roles of a user

    Args:
        user_id (str): The id of the user
        scope (str): The scope of the role
        scope_id (str | None): The id of the scope

    Returns:
        The roles of the user
    """
    return [str(role.role_id) for role in model.UserRole.get(user_id, scope, scope_id)]


def is_default_role(role_id: str) -> bool:
    """Check if the role is a default role

    Args:
        role_id (str): The id of the role to check

    Returns:
        True if the role is a default role, False otherwise
    """
    return any(role_id == role.value for role in const.Roles)

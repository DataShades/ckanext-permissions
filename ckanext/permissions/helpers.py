from __future__ import annotations

from ckanext.permissions import const, model, utils


def get_registered_roles() -> dict[str, str]:
    return utils.get_registered_roles()


def get_role_permissions(role_id: str, permission: str) -> bool:
    return model.RolePermission.get(role_id, permission) is not None


def get_user_roles(user_id: str) -> list[str]:
    return [str(role.role_id) for role in model.UserRole.get_by_user(user_id)]


def is_default_role(role_id: str) -> bool:
    """Check if the role is a default role

    Args:
        role_id (str): The id of the role to check

    Returns:
        bool: True if the role is a default role, False otherwise
    """
    return any(role_id == role.value for role in const.Roles)

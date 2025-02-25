from __future__ import annotations

from ckanext.permissions import model, utils


def get_registered_roles() -> dict[str, str]:
    return utils.get_registered_roles()


def get_role_permissions(role: str, permission: str) -> bool:
    return model.RolePermission.get(role, permission) is not None

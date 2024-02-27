from __future__ import annotations

from typing import Optional, TypedDict


class PermissionGroup(TypedDict):
    name: str
    permissions: list["PermissionDefinition"]
    description: Optional[str]


class PermissionDefinition(TypedDict):
    key: str
    label: str
    roles: list[PermissionRoleDefinition]
    description: Optional[str]


class Permission(PermissionDefinition):
    id: str
    group: str


class PermissionRoleDefinition(TypedDict):
    role: str
    state: str


class PermissionRolePayload(PermissionRoleDefinition):
    permission: str


class PermissionRole(PermissionRolePayload):
    id: str

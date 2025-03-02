from __future__ import annotations

from typing import Optional, TypedDict


class PermissionGroup(TypedDict):
    name: str
    permissions: list["PermissionDefinition"]
    description: Optional[str]


class PermissionDefinition(TypedDict, total=False):
    key: str
    label: str
    description: Optional[str]


class PermissionRoleDefinition(TypedDict):
    role: str
    state: str


class PermissionRolePayload(PermissionRoleDefinition):
    permission: str


class PermissionRole(PermissionRolePayload):
    id: str


class Role(TypedDict):
    id: str
    label: str
    description: str

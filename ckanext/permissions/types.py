from __future__ import annotations

from typing import TypedDict

from typing_extensions import NotRequired


class PermissionGroup(TypedDict):
    name: str
    permissions: list[PermissionDefinition]
    description: str | None


class PermissionDefinition(TypedDict):
    key: str
    label: str
    description: NotRequired[str | None]


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

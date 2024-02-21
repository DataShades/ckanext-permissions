from __future__ import annotations

from typing import Optional, TypedDict
from dataclasses import dataclass


class PermissionGroup(TypedDict):
    name: str
    permissions: list["Permission"]
    description: Optional[str]


class Permission(TypedDict):
    id: str
    key: str
    label: str
    group: str
    roles: list[PermissionRole]
    description: Optional[str]


class PermissionRolePayload(TypedDict):
    role: str
    permission: str
    state: str


class PermissionRole(PermissionRolePayload):
    id: str

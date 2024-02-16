from __future__ import annotations

from typing import Optional
from dataclasses import dataclass


@dataclass
class PermissionGroup:
    """Permission group defines a group of permissions, that will be available
    in code and in UI in a permission manage page"""

    title: str
    permissions: list["PermissionItem"]
    description: Optional[str] = None


@dataclass
class PermissionItem:
    """TODO: we are not describing the roles it applied for?
    I guess, there will be a separate way to register new roles for the portal"""

    auth_func: str
    title: str
    description: Optional[str] = None

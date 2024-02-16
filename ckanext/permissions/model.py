from __future__ import annotations

import logging
from typing_extensions import Self, Optional

from sqlalchemy import Column, Text, ForeignKey
from sqlalchemy.orm import Query

import ckan.model as model
from ckan.plugins import toolkit as tk
from ckan.model.types import make_uuid

log = logging.getLogger(__name__)


class Permission(tk.BaseModel):
    __tablename__ = "perm_permission"

    id = Column(Text, primary_key=True, default=make_uuid)
    key = Column(Text, unique=True)

    @classmethod
    def get(cls, key: str) -> Self | None:
        query: Query = model.Session.query(cls).filter(cls.key == key)

        return query.one_or_none()

    @classmethod
    def define_permission(
        cls, key: str, default_roles: Optional[list[str]] = None
    ) -> list[str]:
        """Define a permission with/without default roles"""
        if cls.is_permission_exist(key):
            return cls.get_roles_for_permission(key)

        permission = cls(key=key)

        model.Session.add(permission)
        model.Session.commit()

        if default_roles:
            cls.set_permission_roles(key, default_roles)

        return permission.roles

    @classmethod
    def set_permission_roles(cls, key: str, roles: list[str]) -> list[str]:
        if not cls.is_permission_exist(key):
            model.Session.add(cls(key=key))

        for role in roles:
            Role.create(role=role, permission=key)

        model.Session.commit()

        return cls.get_roles_for_permission(key)

    @classmethod
    def unset_permission(cls, key: str, roles: list[str]) -> list[str]:
        for role in roles:
            if not cls.is_permission_exist(key):
                continue

            permission = cls.get(key=key, role=role)

            model.Session().autoflush = False
            model.Session.delete(permission)

        model.Session.commit()

        return cls.get_roles_for_permission(key)

    @classmethod
    def is_permission_exist(cls, key: str) -> bool:
        return bool(cls.get(key))

    @classmethod
    def get_roles_for_permission(cls, key: str) -> list[str]:
        return cls.get(key).roles

    @property
    def roles(self) -> list[str]:
        return [
            role.role
            for role in model.Session.query(Role)
            .filter(Role.permission == self.key)
            .all()
        ]


class Role(tk.BaseModel):
    __tablename__ = "perm_role"

    id = Column(Text, primary_key=True, default=make_uuid)
    role = Column(Text)
    permission = Column(ForeignKey(Permission.key, ondelete="CASCADE"))

    @classmethod
    def create(cls, role: str, permission: str) -> Self:
        role_permission = cls(role=role, permission=permission)

        model.Session.add(role_permission)
        model.Session.commit()

        return role_permission

from __future__ import annotations

import logging
from typing import Any
from typing_extensions import Self, Optional

from sqlalchemy import Column, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import Query

import ckan.types as types
import ckan.model as model
from ckan.plugins import toolkit as tk
from ckan.model.types import make_uuid

import ckanext.permissions.const as perm_const
import ckanext.permissions.types as perm_types

log = logging.getLogger(__name__)


class PermissionGroup(tk.BaseModel):
    __tablename__ = "perm_permission_group"

    name = Column(Text, primary_key=True)
    description = Column(Text, nullable=True)

    @property
    def permissions(self) -> list[Permission]:
        return (
            model.Session.query(Permission).filter(Permission.group == self.name).all()
        )

    @classmethod
    def get(cls, name: str) -> Self | None:
        query: Query = model.Session.query(cls).filter(cls.name == name)

        return query.one_or_none()

    @classmethod
    def all(cls) -> list[Self]:
        query: Query = model.Session.query(cls).order_by(cls.name)

        return query.all()

    @classmethod
    def define(cls, name: str, description: Optional[str] = None) -> Self:
        if existing_group := cls.get(name):
            return existing_group

        permission_group = cls(name=name, description=description)

        model.Session.add(permission_group)
        model.Session.commit()

        return permission_group

    def delete(self) -> None:
        model.Session().autoflush = False
        model.Session.delete(self)

    def dictize(self, context: types.Context) -> perm_types.PermissionGroup:
        return perm_types.PermissionGroup(
            name=self.name,
            permissions=[
                permission.dictize(context) for permission in self.permissions
            ],
            description=self.description,
        )


class Permission(tk.BaseModel):
    __tablename__ = "perm_permission"

    id = Column(Text, primary_key=True, default=make_uuid)
    key = Column(Text, unique=True)
    label = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    group = Column(Text, ForeignKey("perm_permission_group.name"))

    @classmethod
    def get(cls, key: str) -> Self | None:
        query: Query = model.Session.query(cls).filter(cls.key == key)

        return query.one_or_none()

    @classmethod
    def define_permission(
        cls,
        key: str,
        group: str,
        label: Optional[str] = None,
        description: Optional[str] = None,
        roles: Optional[list[str]] = None,
    ) -> Self:
        """Define a permission with/without default roles"""
        if permission := cls.get(key=key):
            return permission

        permission = cls(key=key, group=group, label=label, description=description)

        model.Session.add(permission)
        model.Session.commit()

        if roles:
            cls.set_permission_roles(key, roles)

        return permission

    @classmethod
    def set_permission_roles(cls, key: str, roles: list[str]) -> list[str]:
        if not cls.is_permission_exist(key):
            model.Session.add(cls(key=key))

        for role in roles:
            Role.create(role=role, permission=key)

        model.Session.commit()

        return cls.get_roles_for_permission(key)

    @classmethod
    def unset_permission_roles(cls, key: str, roles: list[str]) -> list[str]:
        for role in roles:
            role = Role.get(role=role, permission=key)

            if not role:
                continue

            role.delete()

        model.Session.commit()

        return cls.get_roles_for_permission(key)

    @classmethod
    def is_permission_exist(cls, key: str) -> bool:
        return bool(cls.get(key))

    @classmethod
    def get_roles_for_permission(cls, key: str) -> list[str]:
        permission = cls.get(key)

        return permission.roles if permission else []

    @property
    def roles(self) -> list[str]:
        return [
            role.role
            for role in model.Session.query(Role)
            .filter(Role.permission == self.key)
            .all()
        ]

    def dictize(self, context: types.Context) -> perm_types.Permission:
        return perm_types.Permission(
            id=self.id,
            key=self.key,
            label=self.label,
            description=self.description,
            group=self.group,
            roles=self.roles,
        )


class Role(tk.BaseModel):
    __tablename__ = "perm_role"

    id = Column(Text, primary_key=True, default=make_uuid)
    role = Column(Text)
    permission = Column(ForeignKey(Permission.key, ondelete="CASCADE"))
    state = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(state.in_(perm_const.ROLE_STATES), name="check_status"),
    )

    @classmethod
    def create(cls, role: str, permission: str) -> Self:
        role_permission = cls(role=role, permission=permission)

        model.Session.add(role_permission)
        model.Session.commit()

        return role_permission

    @classmethod
    def get(cls, role: str, permission: str) -> Self | None:
        query: Query = (
            model.Session.query(cls)
            .filter(cls.role == role)
            .filter(cls.permission == permission)
        )

        return query.one_or_none()

    @classmethod
    def unset(cls, role: str, permission: str) -> None:
        role_permission = cls.get(role=role, permission=permission)

        if not role_permission:
            return

        role_permission.delete()
        model.Session.commit()

    def delete(self) -> None:
        model.Session().autoflush = False
        model.Session.delete(self)

    def dictize(self, context: types.Context) -> perm_types.PermissionRole:
        return perm_types.PermissionRole(
            id=self.id,
            role=self.role,
            permission=self.permission,
            state=self.state,
        )

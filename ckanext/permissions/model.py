from __future__ import annotations

import logging

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import Query
from typing_extensions import Self

import ckan.model as model
import ckan.types as types
from ckan.plugins import toolkit as tk

import ckanext.permissions.types as perm_types

log = logging.getLogger(__name__)


class Role(tk.BaseModel):
    __tablename__ = "perm_role"

    id = Column(String, primary_key=True)
    label = Column(String, nullable=False)
    description = Column(String, nullable=False)

    @classmethod
    def create(cls, role_id: str, label: str, description: str) -> Self:
        role = cls(id=role_id, label=label, description=description)

        model.Session.add(role)
        model.Session.commit()

        return role

    @classmethod
    def all(cls) -> list[Self]:
        return [role.dictize({}) for role in model.Session.query(cls).all()]

    def dictize(self, context: types.Context) -> perm_types.Role:
        return perm_types.Role(
            id=str(self.id),
            label=str(self.label),
            description=str(self.description),
        )

    def delete(self) -> None:
        model.Session().autoflush = False
        model.Session.delete(self)


class UserRole(tk.BaseModel):
    __tablename__ = "perm_user_role"

    user = Column(String, ForeignKey("user.id"), primary_key=True)
    role = Column(String, ForeignKey("perm_role.id"), primary_key=True)

    @classmethod
    def get(cls, user: str, role: str) -> Self | None:
        query: Query = model.Session.query(cls).filter(
            cls.user == user, cls.role == role
        )

        return query.one_or_none()

    @classmethod
    def create(cls, user: str, role: str) -> Self:
        user_role = cls(user=user, role=role)

        model.Session.add(user_role)
        model.Session.commit()

        return user_role

    def delete(self) -> None:
        model.Session().autoflush = False
        model.Session.delete(self)


class RolePermission(tk.BaseModel):
    __tablename__ = "perm_role_permission"

    role = Column(String, ForeignKey("perm_role.id"), primary_key=True)
    permission = Column(String, primary_key=True)

    @classmethod
    def get(cls, role: str, permission: str) -> Self | None:
        query: Query = model.Session.query(cls).filter(
            cls.role == role, cls.permission == permission
        )

        return query.one_or_none()

    @classmethod
    def create(cls, role: str, permission: str, defer_commit: bool = True) -> Self:
        role_permission = cls(role=role, permission=permission)

        model.Session.add(role_permission)

        if defer_commit:
            model.Session.commit()

        return role_permission

    def delete(self) -> None:
        model.Session().autoflush = False
        model.Session.delete(self)

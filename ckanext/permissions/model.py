from __future__ import annotations

import logging

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import Query, backref, relationship
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
    def create(cls, data: dict[str, str]) -> Self:
        role = cls(**data)

        model.Session.add(role)
        model.Session.commit()

        return role

    @classmethod
    def get(cls, role: str) -> Self | None:
        return model.Session.query(cls).filter(cls.id == role).one_or_none()

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
        model.Session.delete(self)
        model.Session.commit()


class UserRole(tk.BaseModel):
    __tablename__ = "perm_user_role"

    user_id = Column(
        String, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    role_id = Column(
        String, ForeignKey("perm_role.id", ondelete="CASCADE"), primary_key=True
    )

    user = relationship(
        model.User,
        backref=backref("roles", cascade="all, delete"),
    )

    role = relationship(Role, cascade="all, delete")

    @classmethod
    def get_by_user(cls, user_id: str) -> list[Self]:
        return model.Session.query(cls).filter(cls.user_id == user_id).all()

    @classmethod
    def create(cls, user_id: str, role: str) -> Self:
        for user_role in cls.get_by_user(user_id):
            if user_role.role_id != role:
                continue

            return user_role

        user_role = cls(user_id=user_id, role_id=role)

        model.Session.add(user_role)
        model.Session.commit()

        return user_role

    @classmethod
    def clear_user_roles(cls, user_id: str) -> None:
        model.Session.query(UserRole).filter(UserRole.user_id == user_id).delete()
        model.Session.commit()

    @classmethod
    def delete(cls, user_id: str, role: str) -> None:
        model.Session.query(cls).filter(
            cls.user_id == user_id, cls.role_id == role
        ).delete()
        model.Session.commit()


class RolePermission(tk.BaseModel):
    __tablename__ = "perm_role_permission"

    role_id = Column(String, ForeignKey("perm_role.id"), primary_key=True)
    permission = Column(String, primary_key=True)

    @classmethod
    def get(cls, role_id: str, permission: str) -> Self | None:
        query: Query = model.Session.query(cls).filter(
            cls.role_id == role_id, cls.permission == permission
        )

        return query.one_or_none()

    @classmethod
    def create(cls, role_id: str, permission: str, defer_commit: bool = True) -> Self:
        role_permission = cls(role_id=role_id, permission=permission)

        model.Session.add(role_permission)

        if defer_commit:
            model.Session.commit()

        return role_permission

    def delete(self) -> None:
        model.Session().autoflush = False
        model.Session.delete(self)

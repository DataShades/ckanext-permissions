from __future__ import annotations

import logging

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import Query, backref, relationship
from typing_extensions import Self

from ckan import model, types
from ckan.plugins import toolkit as tk

import ckanext.permissions.const as perm_const
import ckanext.permissions.types as perm_types

log = logging.getLogger(__name__)


class Role(tk.BaseModel):
    __tablename__ = "perm_role"

    id = Column(String, primary_key=True)
    label = Column(String, nullable=False)
    description = Column(String, nullable=False)

    @classmethod
    def create(cls, id: str, label: str, description: str, commit: bool = True) -> Self:
        role = cls(id=id, label=label, description=description)

        model.Session.add(role)

        if commit:
            model.Session.commit()

        return role

    @classmethod
    def get(cls, role: str) -> Self | None:
        return model.Session.query(cls).filter(cls.id == role).one_or_none()

    @classmethod
    def all(cls) -> list[perm_types.Role]:
        return [role.dictize({}) for role in model.Session.query(cls).all()]

    def update(self, description: str) -> None:
        self.description = description

        model.Session.commit()

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

    user_id = Column(String, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(String, ForeignKey("perm_role.id", ondelete="CASCADE"), primary_key=True)

    scope = Column(String, primary_key=True, default=perm_const.SCOPE_GLOBAL)
    scope_id = Column(String, primary_key=True, default="", server_default="")

    user = relationship(
        model.User,
        backref=backref("roles", cascade="all, delete"),
    )

    role = relationship(Role)

    @classmethod
    def get(cls, user_id: str, scope: str = perm_const.SCOPE_GLOBAL, scope_id: str | None = None) -> list[Self]:
        query: Query = model.Session.query(cls).filter(cls.user_id == user_id).filter(cls.scope == scope)

        if scope_id:
            query = query.filter(cls.scope_id == scope_id)

        return query.all()

    @classmethod
    def get_for_users(
        cls, user_ids: list[str], scope: str = perm_const.SCOPE_GLOBAL, scope_id: str | None = None
    ) -> dict[str, list[str]]:
        query: Query = model.Session.query(cls).filter(cls.user_id.in_(user_ids), cls.scope == scope)

        if scope_id:
            query = query.filter(cls.scope_id == scope_id)

        roles: dict[str, list[str]] = {}

        for user_role in query:
            roles.setdefault(str(user_role.user_id), []).append(str(user_role.role_id))

        return roles

    @classmethod
    def has_permission(
        cls, user_id: str, permission: str, scope: str = perm_const.SCOPE_GLOBAL, scope_id: str | None = None
    ) -> bool:
        query = cls._with_permissions(user_id, [permission], scope)
        query = query.filter(cls.scope_id == (scope_id or ""))

        return bool(model.Session.query(query.exists()).scalar())

    @classmethod
    def get_scope_ids_with_permissions(cls, user_id: str, permissions: list[str], scope: str) -> set[str]:
        query = (
            cls._with_permissions(user_id, permissions, scope)
            .filter(cls.scope_id != "")
            .with_entities(cls.scope_id)
            .distinct()
        )

        return {str(scope_id) for (scope_id,) in query}

    @classmethod
    def _with_permissions(cls, user_id: str, permissions: list[str], scope: str) -> Query:
        return (
            model.Session.query(cls)
            .join(RolePermission, RolePermission.role_id == cls.role_id)
            .filter(cls.user_id == user_id, cls.scope == scope, RolePermission.permission.in_(permissions))
        )

    @classmethod
    def create(
        cls,
        user_id: str,
        role: str,
        scope: str = perm_const.SCOPE_GLOBAL,
        scope_id: str | None = None,
        commit: bool = True,
    ) -> Self:
        query: Query = model.Session.query(cls).filter(cls.user_id == user_id, cls.role_id == role, cls.scope == scope)

        if scope_id:
            query = query.filter(cls.scope_id == scope_id)

        if existing := query.first():
            return existing

        user_role = cls(user_id=user_id, role_id=role, scope=scope, scope_id=scope_id or "")

        model.Session.add(user_role)

        if commit:
            model.Session.commit()

        return user_role

    @classmethod
    def clear_user_roles(cls, user_id: str, scope: str = "", scope_id: str | None = None, commit: bool = True) -> None:
        perm = model.Session.query(UserRole).filter(UserRole.user_id == user_id)

        if scope:
            perm = perm.filter_by(scope=scope)
            if scope_id:
                perm = perm.filter_by(scope_id=scope_id)

        perm.delete()

        if commit:
            model.Session.commit()

    @classmethod
    def delete(cls, user_id: str, role: str, scope: str = perm_const.SCOPE_GLOBAL, scope_id: str | None = None) -> None:
        query: Query = model.Session.query(cls).filter(cls.user_id == user_id, cls.role_id == role, cls.scope == scope)

        if scope_id:
            query = query.filter(cls.scope_id == scope_id)

        query.delete()
        model.Session.commit()


class RolePermission(tk.BaseModel):
    __tablename__ = "perm_role_permission"

    role_id = Column(String, ForeignKey("perm_role.id"), primary_key=True)
    permission = Column(String, primary_key=True)

    @classmethod
    def get(cls, role_id: str, permission: str) -> Self | None:
        query: Query = model.Session.query(cls).filter(cls.role_id == role_id, cls.permission == permission)

        return query.one_or_none()

    @classmethod
    def create(cls, role_id: str, permission: str, commit: bool = True) -> Self:
        role_permission = cls(role_id=role_id, permission=permission)

        model.Session.add(role_permission)

        if commit:
            model.Session.commit()

        return role_permission

    def delete(self, commit: bool = True) -> None:
        model.Session.delete(self)

        if commit:
            model.Session.commit()

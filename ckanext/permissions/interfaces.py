from __future__ import annotations

from abc import abstractmethod

import ckan.model as model
from ckan.plugins.interfaces import Interface

import ckanext.permissions.const as perm_const
from ckanext.permissions.types import PermissionGroup


class IPermissions(Interface):
    @abstractmethod
    def get_permission_group(self) -> PermissionGroup:
        """The method must return a PermissionGroup dataclass"""

    def define_user_role(self, user: model.User) -> str:
        """"""
        return perm_const.ROLE_USER

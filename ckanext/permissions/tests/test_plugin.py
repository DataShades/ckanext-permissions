from __future__ import annotations

import pytest

import ckan.plugins.toolkit as tk
from ckan.tests.helpers import call_action

import ckanext.permissions.const as const
import ckanext.permissions.types as perm_types

from .conftest import PermissionTestPlugin


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPermissionCheck:
    """Each permission must belong to a permission group.
    We are implementing this to facilitate later rendering in the UI."""

    def _set_role_state(self, perm_key: str, role: str, state: str) -> None:
        call_action(
            "permission_set_roles",
            key=perm_key,
            roles=[{"role": role, "state": state}],
        )

    def test_anon(self, permission: perm_types.Permission, user):
        """The permission factory comes with anon role disallow.
        TODO: rn it works only with auth_allow_anonymous_access on auth func"""
        PermissionTestPlugin.permission_auth_called = 0

        with pytest.raises(
            tk.NotAuthorized, match="Users with role anonymous are not allowed"
        ):
            call_action("permission_test", {"ignore_auth": False, "user": None})

        assert PermissionTestPlugin.permission_auth_called == 0

        self._set_role_state(permission["key"], const.ROLE_ANON, const.STATE_ALLOW)
        call_action("permission_test", {"ignore_auth": False, "user": None})
        assert PermissionTestPlugin.permission_auth_called == 0

        self._set_role_state(permission["key"], const.ROLE_ANON, const.STATE_IGNORE)
        call_action("permission_test", {"ignore_auth": False, "user": None})
        assert PermissionTestPlugin.permission_auth_called == 1

    def test_regular_user(self, permission: perm_types.Permission, user):
        """The permission factory comes with anon role disallow"""
        PermissionTestPlugin.permission_auth_called = 0

        self._set_role_state(permission["key"], const.ROLE_USER, const.STATE_DISALLOW)

        with pytest.raises(
            tk.NotAuthorized, match="Users with role user are not allowed"
        ):
            call_action("permission_test", {"ignore_auth": False, "user": user["name"]})

        assert PermissionTestPlugin.permission_auth_called == 0

        self._set_role_state(permission["key"], const.ROLE_USER, const.STATE_ALLOW)
        call_action("permission_test", {"ignore_auth": False, "user": user["name"]})
        assert PermissionTestPlugin.permission_auth_called == 0

        self._set_role_state(permission["key"], const.ROLE_USER, const.STATE_IGNORE)
        call_action("permission_test", {"ignore_auth": False, "user": user["name"]})
        assert PermissionTestPlugin.permission_auth_called == 1

    def test_sysadmin_user(self, permission: perm_types.Permission, sysadmin):
        """TODO: rn it works only with auth_sysadmins_check on auth func"""
        PermissionTestPlugin.permission_auth_called = 0

        self._set_role_state(
            permission["key"], const.ROLE_SYSADMIN, const.STATE_DISALLOW
        )

        with pytest.raises(
            tk.NotAuthorized, match="Users with role sysadmin are not allowed"
        ):
            call_action(
                "permission_test", {"ignore_auth": False, "user": sysadmin["name"]}
            )

        assert PermissionTestPlugin.permission_auth_called == 0

        self._set_role_state(permission["key"], const.ROLE_SYSADMIN, const.STATE_ALLOW)
        call_action("permission_test", {"ignore_auth": False, "user": sysadmin["name"]})
        assert PermissionTestPlugin.permission_auth_called == 0

        self._set_role_state(permission["key"], const.ROLE_SYSADMIN, const.STATE_IGNORE)
        call_action("permission_test", {"ignore_auth": False, "user": sysadmin["name"]})
        assert PermissionTestPlugin.permission_auth_called == 1

    def test_check_anon_func_with_user(self, permission: perm_types.Permission, user):
        self._set_role_state(permission["key"], const.ROLE_ANON, const.STATE_IGNORE)
        self._set_role_state(permission["key"], const.ROLE_USER, const.STATE_IGNORE)

        PermissionTestPlugin.permission_auth_called = 0

        call_action("permission_test", {"ignore_auth": False, "user": None})
        assert PermissionTestPlugin.permission_auth_called == 1
        call_action("permission_test", {"ignore_auth": False, "user": user["name"]})
        assert PermissionTestPlugin.permission_auth_called == 2

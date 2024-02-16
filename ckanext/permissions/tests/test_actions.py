import pytest

import ckan.plugins.toolkit as tk
from ckan.tests.helpers import call_action

import ckanext.permissions.const as perm_const


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPermissionDefine:
    def test_define(self):
        result = call_action("permission_define", key="test_1")

        assert result["key"] == "test_1"
        assert result["roles"] == []

    def test_define_with_default_roles(self):
        result = call_action(
            "permission_define",
            key="test_2",
            roles=[perm_const.ROLE_ANON, perm_const.ROLE_SYSADMIN],
        )

        assert result["key"] == "test_2"
        assert result["roles"] == [perm_const.ROLE_ANON, perm_const.ROLE_SYSADMIN]

    # def test_basic_set_no_roles(self):
    #     with pytest.raises(tk.ValidationError, match="Missing value"):
    #         call_action("permission_set", key="xxx")

    # def test_basic_set_not_allowed_role(self):
    #     with pytest.raises(tk.ValidationError, match="The role xxx is not supported"):
    #         call_action("permission_set", key="xxx", roles=["xxx"])

    # def test_basic_set_no_key(self):
    #     with pytest.raises(tk.ValidationError, match="Missing value"):
    #         call_action("permission_set", roles=[perm_const.ROLE_ANON])

    # def test_existing_key_no_error(self):
    #     call_action("permission_set", key="xxx", roles=[perm_const.ROLE_ANON])
    #     call_action("permission_set", key="xxx", roles=[perm_const.ROLE_ANON])

    # def test_existing_key_extend_roles(self):
    #     result = call_action("permission_set", key="xxx", roles=[perm_const.ROLE_ANON])

    #     assert result["roles"] == [perm_const.ROLE_ANON]

    #     result = call_action(
    #         "permission_set",
    #         key="xxx",
    #         roles=[perm_const.ROLE_ANON, perm_const.ROLE_SYSADMIN],
    #     )

    #     assert result["roles"] == [perm_const.ROLE_ANON, perm_const.ROLE_SYSADMIN]

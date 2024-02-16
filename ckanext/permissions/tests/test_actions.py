import pytest

import ckan.plugins.toolkit as tk
from ckan.tests.helpers import call_action

import ckanext.permissions.const as perm_const
import ckanext.permissions.types as perm_types


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPermissionGroupDefine:
    """Each permission must belong to a permission group.
    We are implementing this to facilitate later rendering in the UI."""

    def test_define(self):
        result = call_action(
            "permission_group_define", name="test_group", description="xxx"
        )

        assert result["name"] == "test_group"
        assert result["description"] == "xxx"
        assert result["permissions"] == []

    def test_define_without_description(self):
        result = call_action("permission_group_define", name="test_group")

        assert result["name"] == "test_group"
        assert not result["description"]
        assert result["permissions"] == []

    def test_define_without_name(self):
        with pytest.raises(tk.ValidationError):
            call_action("permission_group_define")

    def test_define_same_group_name(self):
        """Do not create a permission group or show an error if the group
        already exists"""
        call_action("permission_group_define", name="test_group")
        call_action("permission_group_define", name="test_group")

        result = call_action("permision_group_list")

        assert len(result) == 1


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPermissionDefine:
    def test_define_basic(self, permission_group: perm_types.PermissionGroup):
        result: perm_types.Permission = call_action(
            "permission_define",
            key="perm_1",
            label="xxx",
            description="xxx",
            group=permission_group["name"],
            roles=[perm_const.ROLE_ANON, perm_const.ROLE_SYSADMIN],
        )

        assert result["id"]
        assert result["key"] == "perm_1"
        assert result["label"] == "xxx"
        assert result["description"] == "xxx"
        assert result["group"] == permission_group["name"]
        assert result["roles"] == [perm_const.ROLE_ANON, perm_const.ROLE_SYSADMIN]

    def test_without_optional_args(self, permission_group: perm_types.PermissionGroup):
        result: perm_types.Permission = call_action(
            "permission_define",
            key="perm_2",
            group=permission_group["name"],
        )

        assert result["key"] == "perm_2"
        assert not result["description"]
        assert not result["label"]

    def test_without_group(self):
        with pytest.raises(tk.ValidationError) as e:
            call_action("permission_define", key="perm_2")

        assert e.value.error_dict == {"group": ["Missing value"]}

    def test_without_non_existent_group(self):
        with pytest.raises(
            tk.ValidationError, match="Permission group xxx doesn't exist"
        ):
            call_action("permission_define", key="perm_2", group="xxx")

    # def test_define_with_default_roles(self, permission_group):
    #     result = call_action(
    #         "permission_group_define",
    #         key="test_2",
    #         roles=[perm_const.ROLE_ANON, perm_const.ROLE_SYSADMIN],
    #     )

    #     assert result["key"] == "test_2"
    #     assert result["roles"] == [perm_const.ROLE_ANON, perm_const.ROLE_SYSADMIN]

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

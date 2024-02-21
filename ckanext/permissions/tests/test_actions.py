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
            roles=[
                {"role": perm_const.ROLE_ANON, "state": perm_const.STATE_DISALLOW},
                {"role": perm_const.ROLE_SYSADMIN, "state": perm_const.STATE_ALLOW},
            ],
        )

        assert result["id"]
        assert result["key"] == "perm_1"
        assert result["label"] == "xxx"
        assert result["description"] == "xxx"
        assert result["group"] == permission_group["name"]

        for role in result["roles"]:
            assert role["permission"] == "perm_1"
            assert role["role"]
            assert role["state"]

    def test_without_optional_args(self, permission_group: perm_types.PermissionGroup):
        result: perm_types.Permission = call_action(
            "permission_define",
            key="perm_2",
            group=permission_group["name"],
        )

        assert result["key"] == "perm_2"
        assert not result["description"]
        assert not result["label"]
        assert not result["roles"]

    def test_without_group(self):
        with pytest.raises(tk.ValidationError) as e:
            call_action("permission_define", key="perm_2")

        assert e.value.error_dict == {"group": ["Missing value"]}

    def test_without_non_existent_group(self):
        with pytest.raises(
            tk.ValidationError, match="Permission group xxx doesn't exist"
        ):
            call_action("permission_define", key="perm_2", group="xxx")


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPermissionSetRoles:
    def test_set_roles_basic(self, permission: perm_types.Permission):
        result: perm_types.Permission = call_action(
            "permission_set_roles",
            key=permission["key"],
            roles=[
                {"role": perm_const.ROLE_ANON, "state": perm_const.STATE_DISALLOW},
                {"role": perm_const.ROLE_SYSADMIN, "state": perm_const.STATE_ALLOW},
            ],
        )

        # permission factory comes with anon role, so nothing should break
        # if we are setting it again
        assert len(result["roles"]) == 2
        assert result["roles"][0]["id"]
        assert result["roles"][0]["permission"] == permission["key"]
        assert result["roles"][0]["role"] == perm_const.ROLE_ANON
        assert result["roles"][0]["state"] == perm_const.STATE_DISALLOW

    def test_set_roles_for_not_existing_permission(self):
        with pytest.raises(tk.ValidationError, match="Permission xxx doesn't exist"):
            call_action(
                "permission_set_roles",
                key="xxx",
                roles=[
                    {"role": perm_const.ROLE_ANON, "state": perm_const.STATE_DISALLOW},
                    {"role": perm_const.ROLE_SYSADMIN, "state": perm_const.STATE_ALLOW},
                ],
            )

    def test_set_unsupported_role(self, permission: perm_types.Permission):
        with pytest.raises(
            tk.ValidationError, match="The role passerby is not supported"
        ):
            call_action(
                "permission_set_roles",
                key=permission["key"],
                roles=[
                    {"role": "passerby", "state": perm_const.STATE_ALLOW},
                ],
            )

    def test_set_updates_state(self, permission: perm_types.Permission):
        """The permission factory comes with anon role. Check if we can just
        replace the state for role."""
        result: perm_types.Permission = call_action(
            "permission_set_roles",
            key=permission["key"],
            roles=[
                {"role": perm_const.ROLE_ANON, "state": perm_const.STATE_ALLOW},
            ],
        )

        assert len(result["roles"]) == 1
        assert result["roles"][0]["state"] == perm_const.STATE_ALLOW

    def test_set_multiple_identic_roles(self, permission: perm_types.Permission):
        result: perm_types.Permission = call_action(
            "permission_set_roles",
            key=permission["key"],
            roles=[
                {"role": perm_const.ROLE_ANON, "state": perm_const.STATE_DISALLOW},
                {"role": perm_const.ROLE_ANON, "state": perm_const.STATE_DISALLOW},
                {"role": perm_const.ROLE_ANON, "state": perm_const.STATE_DISALLOW},
                {"role": perm_const.ROLE_ANON, "state": perm_const.STATE_ALLOW},
            ],
        )

        assert len(result["roles"]) == 1
        assert result["roles"][0]["state"] == perm_const.STATE_ALLOW


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPermissionUnsetRoles:
    def test_unset_roles_basic(self, permission: perm_types.Permission):
        result: perm_types.Permission = call_action(
            "permission_unset_roles",
            key=permission["key"],
            roles=[
                {"role": perm_const.ROLE_ANON, "state": perm_const.STATE_DISALLOW},
            ],
        )

        # permission factory comes with anon role
        assert len(result["roles"]) == 0

    def test_unset_roles_for_not_existing_permission(self):
        with pytest.raises(tk.ValidationError, match="Permission xxx doesn't exist"):
            call_action(
                "permission_unset_roles",
                key="xxx",
                roles=[
                    {"role": perm_const.ROLE_ANON, "state": perm_const.STATE_DISALLOW},
                    {"role": perm_const.ROLE_SYSADMIN, "state": perm_const.STATE_ALLOW},
                ],
            )

    def test_unset_unsupported_role(self, permission: perm_types.Permission):
        with pytest.raises(
            tk.ValidationError, match="The role passerby is not supported"
        ):
            call_action(
                "permission_unset_roles",
                key=permission["key"],
                roles=[
                    {"role": "passerby", "state": perm_const.STATE_ALLOW},
                ],
            )

    def test_unset_not_setted_role(self, permission: perm_types.Permission):
        """No reason to throw an exception in this case, just do nothing"""
        result: perm_types.Permission = call_action(
            "permission_unset_roles",
            key=permission["key"],
            roles=[
                {"role": perm_const.ROLE_SYSADMIN, "state": perm_const.STATE_ALLOW},
            ],
        )

        assert len(result["roles"]) == 1
        assert result["roles"][0]["role"] == perm_const.ROLE_ANON

    def test_unset_multiple_identic_roles(self, permission: perm_types.Permission):
        result: perm_types.Permission = call_action(
            "permission_unset_roles",
            key=permission["key"],
            roles=[
                {"role": perm_const.ROLE_ANON, "state": perm_const.STATE_DISALLOW},
                {"role": perm_const.ROLE_ANON, "state": perm_const.STATE_DISALLOW},
                {"role": perm_const.ROLE_ANON, "state": perm_const.STATE_DISALLOW},
            ],
        )

        assert len(result["roles"]) == 0

from typing import cast

import pytest

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.tests.helpers import call_action

from ckanext.permissions import const, utils
from ckanext.permissions.types import PermissionDefinition, PermissionGroup
from ckanext.permissions.utils import validate_groups


@pytest.mark.usefixtures("with_plugins")
class TestParsePermissionGroupSchemas:
    def test_valid_schema(self):
        assert utils.parse_permission_group_schemas()


@pytest.mark.usefixtures("with_plugins")
class TestParsePermissionGroupsValidation:
    def test_valid_group(self):
        validate_groups(
            {
                "new_group": PermissionGroup(
                    name="xxx",
                    description="xxx",
                    permissions=[
                        PermissionDefinition(
                            key="xxx",
                            label="xxx",
                            description="xxx",
                        )
                    ],
                )
            }
        )

    def test_group_missing_name(self):
        with pytest.raises(tk.ValidationError, match="Missing value"):
            validate_groups(
                {
                    "new_group": PermissionGroup(
                        name="",
                        description="xxx",
                        permissions=[],
                    )
                }
            )

    def test_group_missing_description(self):
        with pytest.raises(tk.ValidationError, match="Missing value"):
            validate_groups(
                {
                    "new_group": PermissionGroup(
                        name="xxx",
                        description="",
                        permissions=[],
                    )
                }
            )

    def test_group_missing_permissions(self):
        with pytest.raises(tk.ValidationError, match="Missing permissions"):
            validate_groups(
                {
                    "new_group": PermissionGroup(
                        name="xxx",
                        description="xxx",
                        permissions=[],
                    )
                }
            )

    def test_group_permissions_empty_list(self):
        with pytest.raises(tk.ValidationError, match="Missing permissions"):
            validate_groups(
                {
                    "new_group": PermissionGroup(
                        name="xxx",
                        description="xxx",
                        permissions=[],
                    )
                }
            )

    def test_missing_permission_key(self):
        with pytest.raises(tk.ValidationError, match="Missing value"):
            validate_groups(
                {
                    "new_group": PermissionGroup(
                        name="xxx",
                        description="xxx",
                        permissions=[
                            PermissionDefinition(
                                key="",
                                label="xxx",
                                description="xxx",
                            )
                        ],
                    )
                }
            )

    def test_missing_permission_label(self):
        with pytest.raises(tk.ValidationError, match="Missing value"):
            validate_groups(
                {
                    "new_group": PermissionGroup(
                        name="xxx",
                        description="xxx",
                        permissions=[PermissionDefinition(key="xxx", label="", description="xxx")],
                    )
                }
            )

    def test_allow_empty_permission_description(self):
        validate_groups(
            {
                "new_group": PermissionGroup(
                    name="xxx",
                    description="xxx",
                    permissions=[PermissionDefinition(key="xxx", label="xxx", description="")],
                ),
            }
        )


@pytest.mark.usefixtures("with_plugins")
class TestLoadSchemas:
    def test_valid_schemas(self):
        assert utils._load_schemas(
            [
                "ckanext.permissions:tests/data/test_group.yaml",
                "ckanext.permissions:default_group.yaml",
            ],
            "name",
        )

    def test_nonexistent_file(self):
        result = utils._load_schemas(["ckanext.permissions:tests:missing.yaml"], "name")
        assert result == {}


@pytest.mark.usefixtures("with_plugins")
class TestLoadSchema:
    def test_valid_schema(self):
        assert utils._load_schema(
            "ckanext.permissions:tests/data/test_group.yaml",
        )

    def test_nonexistent_file(self):
        assert not utils._load_schema(
            "ckanext.permissions:tests/data/missing.yaml",
        )


@pytest.mark.usefixtures("with_plugins")
class TestGetPermissionGroups:
    def test_get_permission_groups(self):
        result = utils.get_permission_groups()
        assert isinstance(result, list)


@pytest.mark.usefixtures("with_plugins")
class TestGetPermissions:
    def test_get_permissions(self):
        result = utils.get_permissions()

        assert isinstance(result, dict)
        assert result["perm_1"] == PermissionDefinition(key="perm_1", label="Permission 1")


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestCheckPermission:
    def test_set_permission(self):
        anon_user = model.AnonymousUser()
        assert not utils.check_permission("perm_1", anon_user)

        call_action(
            "permissions_update",
            permissions={"perm_1": {const.Roles.Anonymous.value: True}},
        )

        assert utils.check_permission("perm_1", anon_user)

    def test_scoped_role(self, user_factory, test_role, organization_factory):
        from ckanext.permissions import model as perm_model

        user = cast(model.User, model.User.get(user_factory()["id"]))
        org = organization_factory()
        other_org = organization_factory()

        call_action(
            "permissions_update",
            permissions={"perm_1": {test_role["id"]: True}},
        )
        perm_model.UserRole.create(user.id, test_role["id"], const.SCOPE_ORGANIZATION, org["id"])

        assert utils.check_permission("perm_1", user, const.SCOPE_ORGANIZATION, org["id"])
        assert not utils.check_permission("perm_1", user, const.SCOPE_ORGANIZATION, other_org["id"])
        assert not utils.check_permission("perm_1", user, "org", org["id"])
        assert not utils.check_permission("perm_1", user)


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestEnsureDefaultRoles:
    def test_creates_default_roles(self, reset_db, migrate_db_for):
        """Test that ensure_default_roles creates all default roles."""
        from ckanext.permissions import model as perm_model

        for role in perm_model.Role.all():
            perm_model.Role.delete(perm_model.Role.get(role["id"]))

        assert len(perm_model.Role.all()) == 0

        created_count = utils.ensure_default_roles()

        assert created_count == 3

        assert perm_model.Role.get("anonymous") is not None
        assert perm_model.Role.get("authenticated") is not None
        assert perm_model.Role.get("administrator") is not None

    def test_reuse(self):
        """Test that ensure_default_roles can be called multiple times."""
        # Call ensure_default_roles after initial call in conftest.py
        addiitonal_call = utils.ensure_default_roles()
        assert addiitonal_call == 0


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestAssignRoleToUser:
    def test_assign_role_to_user(self, user_factory):
        """Test assigning a role to a user."""
        from ckanext.permissions import model as perm_model

        user = user_factory()

        utils.assign_role_to_user(user["id"], const.Roles.Administrator.value)

        user_roles = perm_model.UserRole.get(user["id"])
        role_ids = [role.role_id for role in user_roles]
        assert const.Roles.Administrator.value in role_ids

    def test_assign_duplicate_role(self, user_factory):
        """Test that assigning the same role twice doesn't create duplicates."""
        from ckanext.permissions import model as perm_model

        user = user_factory()

        utils.assign_role_to_user(user["id"], const.Roles.Administrator.value)
        utils.assign_role_to_user(user["id"], const.Roles.Administrator.value)

        user_roles = perm_model.UserRole.get(user["id"])
        role_ids = [role.role_id for role in user_roles]
        assert len(role_ids) == 2

    def test_assign_scoped_role(self, user_factory, organization_factory):
        from ckanext.permissions import model as perm_model

        user = user_factory()
        org = organization_factory()

        utils.assign_role_to_user(user["id"], const.Roles.Administrator.value, const.SCOPE_ORGANIZATION, org["id"])

        org_roles = perm_model.UserRole.get(user["id"], const.SCOPE_ORGANIZATION, org["id"])
        global_roles = perm_model.UserRole.get(user["id"])

        assert [role.role_id for role in org_roles] == [const.Roles.Administrator.value]
        assert const.Roles.Administrator.value not in [role.role_id for role in global_roles]


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRemoveRoleFromUser:
    def test_remove_role_from_user(self, user_factory):
        """Test removing a role from a user."""
        from ckanext.permissions import model as perm_model

        user = user_factory()

        utils.assign_role_to_user(user["id"], const.Roles.Administrator.value)
        utils.remove_role_from_user(user["id"], const.Roles.Administrator.value)

        user_roles = perm_model.UserRole.get(user["id"])
        role_ids = [role.role_id for role in user_roles]
        assert const.Roles.Administrator.value not in role_ids

    def test_remove_role_doesnt_affect_other_roles(self, user_factory, test_role):
        """Test that removing one role doesn't affect other roles."""
        from ckanext.permissions import model as perm_model

        user = user_factory()

        utils.assign_role_to_user(user["id"], const.Roles.Administrator.value)

        utils.remove_role_from_user(user["id"], const.Roles.Administrator.value)

        # Verify only the correct role was removed
        user_roles = perm_model.UserRole.get(user["id"])
        role_ids = [role.role_id for role in user_roles]
        assert const.Roles.Administrator.value not in role_ids
        assert const.Roles.Authenticated.value in role_ids

    def test_remove_role_keeps_other_scopes(self, user_factory, organization_factory):
        from ckanext.permissions import model as perm_model

        user = user_factory()
        org = organization_factory()
        admin = const.Roles.Administrator.value

        utils.assign_role_to_user(user["id"], admin)
        utils.assign_role_to_user(user["id"], admin, const.SCOPE_ORGANIZATION, org["id"])

        utils.remove_role_from_user(user["id"], admin)

        org_roles = perm_model.UserRole.get(user["id"], const.SCOPE_ORGANIZATION, org["id"])

        assert admin not in [role.role_id for role in perm_model.UserRole.get(user["id"])]
        assert [role.role_id for role in org_roles] == [admin]

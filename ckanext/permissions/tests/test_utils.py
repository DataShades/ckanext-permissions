from typing import cast
from unittest import mock

import pytest

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.tests.helpers import call_action

from ckanext.permissions import const, utils
from ckanext.permissions import model as perm_model
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

    def test_depends_on_permission_in_another_group(self):
        validate_groups(
            {
                "first": PermissionGroup(
                    name="first", description="xxx", permissions=[PermissionDefinition(key="read", label="Read")]
                ),
                "second": PermissionGroup(
                    name="second",
                    description="xxx",
                    permissions=[PermissionDefinition(key="write", label="Write", depends_on=["read"])],
                ),
            }
        )

    def test_unknown_dependency_is_dropped(self):
        permission = PermissionDefinition(key="xxx", label="xxx", depends_on=["missing", "yyy"])
        groups = {
            "new_group": PermissionGroup(
                name="xxx",
                description="xxx",
                permissions=[permission, PermissionDefinition(key="yyy", label="yyy")],
            )
        }

        with mock.patch.object(utils.log, "warning") as warning:
            assert validate_groups(groups)

        assert permission["depends_on"] == ["yyy"]
        assert warning.call_count == 1
        assert warning.call_args.args[1:] == ("xxx", "missing")

    def test_depends_on_itself(self):
        with pytest.raises(tk.ValidationError, match="depends on itself"):
            validate_groups(
                {
                    "new_group": PermissionGroup(
                        name="xxx",
                        description="xxx",
                        permissions=[PermissionDefinition(key="xxx", label="xxx", depends_on=["xxx"])],
                    )
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

        assert [group["name"] for group in result] == ["Test group", "Default group"]


@pytest.mark.usefixtures("with_plugins")
class TestGetPermissions:
    def test_get_permissions(self):
        result = utils.get_permissions()

        assert isinstance(result, dict)
        assert result["perm_1"] == PermissionDefinition(key="perm_1", label="Permission 1")

    def test_get_permission_dependencies(self):
        assert utils.get_permission_dependencies("update_any_dataset") == ["read_any_dataset"]
        assert utils.get_permission_dependencies("delete_any_dataset") == ["read_any_dataset"]
        assert utils.get_permission_dependencies("delete_any_resource") == ["update_any_dataset"]
        assert utils.get_permission_dependencies("perm_1") == []
        assert utils.get_permission_dependencies("missing") == []

    def test_get_permission_dependents(self):
        assert utils.get_permission_dependents("read_any_dataset") == [
            "update_any_dataset",
            "delete_any_dataset",
            "manage_dataset_collaborators",
        ]
        assert utils.get_permission_dependents("update_any_dataset") == ["delete_any_resource", "bulk_update_datasets"]
        assert utils.get_permission_dependents("delete_any_resource") == []


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

    def test_unregistered_permission_is_never_granted(self, user_factory, test_role, organization_factory):
        from ckanext.permissions import model as perm_model

        user = cast(model.User, model.User.get(user_factory()["id"]))
        org = organization_factory()

        perm_model.RolePermission.create(test_role["id"], "removed_permission")
        perm_model.RolePermission.create(const.Roles.Anonymous.value, "removed_permission")
        perm_model.UserRole.create(user.id, test_role["id"])
        perm_model.UserRole.create(user.id, test_role["id"], const.SCOPE_ORGANIZATION, org["id"])

        assert not utils.check_permission("removed_permission", user)
        assert not utils.check_permission("removed_permission", model.AnonymousUser())
        assert not utils.check_organization_permission("removed_permission", user, org["id"])
        assert not utils.get_permission_scope_ids(["removed_permission"], user, const.SCOPE_ORGANIZATION)

    def test_get_unregistered_grants(self, test_role):
        from ckanext.permissions import model as perm_model

        call_action("permissions_update", permissions={"perm_1": {test_role["id"]: True}})
        perm_model.RolePermission.create(test_role["id"], "removed_permission")

        grants = utils.get_unregistered_grants()

        assert [(grant.permission, grant.role_id) for grant in grants] == [("removed_permission", test_role["id"])]

    def test_anonymous_grant_applies_to_logged_in_user(self, user_factory, organization_factory):
        user = cast(model.User, model.User.get(user_factory()["id"]))
        org = organization_factory()

        call_action(
            "permissions_update",
            permissions={"perm_1": {const.Roles.Anonymous.value: True}},
        )

        assert utils.check_permission("perm_1", user)
        assert not utils.check_permission("perm_1", user, const.SCOPE_ORGANIZATION, org["id"])
        assert utils.check_organization_permission("perm_1", user, org["id"])

    def test_authenticated_grant_applies_to_every_logged_in_user(self, user_factory, organization_factory):
        user = cast(model.User, model.User.get(user_factory()["id"]))
        org = organization_factory()

        call_action("permissions_update", permissions={"perm_1": {const.Roles.Authenticated.value: True}})

        assert utils.check_permission("perm_1", user)
        assert not utils.check_permission("perm_1", model.AnonymousUser())
        assert not utils.check_permission("perm_1", user, const.SCOPE_ORGANIZATION, org["id"])
        assert utils.check_organization_permission("perm_1", user, org["id"])

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
        assert role_ids.count(const.Roles.Administrator.value) == 1

    def test_assign_scoped_role(self, user_factory, organization_factory):
        from ckanext.permissions import model as perm_model

        user = user_factory()
        org = organization_factory()

        utils.assign_role_to_user(user["id"], const.Roles.Administrator.value, const.SCOPE_ORGANIZATION, org["id"])

        org_roles = perm_model.UserRole.get(user["id"], const.SCOPE_ORGANIZATION, org["id"])
        global_roles = perm_model.UserRole.get(user["id"])

        assert [role.role_id for role in org_roles] == [const.Roles.Administrator.value]
        assert const.Roles.Administrator.value not in [role.role_id for role in global_roles]

    def test_assign_same_role_in_two_organizations(self, user_factory, organization_factory):
        from ckanext.permissions import model as perm_model

        user = user_factory()
        admin = const.Roles.Administrator.value
        orgs = [organization_factory(), organization_factory()]

        for org in orgs:
            utils.assign_role_to_user(user["id"], admin, const.SCOPE_ORGANIZATION, org["id"])

        for org in orgs:
            org_roles = perm_model.UserRole.get(user["id"], const.SCOPE_ORGANIZATION, org["id"])
            assert [role.role_id for role in org_roles] == [admin]


@pytest.mark.usefixtures("with_plugins")
class TestAnonymousValidation:
    def test_allowed_permission_depends_on_blocked_one(self):
        with pytest.raises(tk.ValidationError, match="allowed for the anonymous role but depends on read"):
            validate_groups(
                {
                    "new_group": PermissionGroup(
                        name="xxx",
                        description="xxx",
                        permissions=[
                            PermissionDefinition(key="read", label="Read", anonymous=False),
                            PermissionDefinition(key="write", label="Write", depends_on=["read"]),
                        ],
                    )
                }
            )

    def test_blocked_permission_depends_on_allowed_one(self):
        validate_groups(
            {
                "new_group": PermissionGroup(
                    name="xxx",
                    description="xxx",
                    permissions=[
                        PermissionDefinition(key="read", label="Read"),
                        PermissionDefinition(key="write", label="Write", depends_on=["read"], anonymous=False),
                    ],
                )
            }
        )

    def test_is_permission_blocked_for_role(self):
        anonymous = const.Roles.Anonymous.value

        assert utils.is_permission_blocked_for_role("update_any_dataset", anonymous)
        assert not utils.is_permission_blocked_for_role("read_private_dataset", anonymous)
        assert not utils.is_permission_blocked_for_role("perm_1", anonymous)
        assert not utils.is_permission_blocked_for_role("missing", anonymous)
        assert not utils.is_permission_blocked_for_role("update_any_dataset", const.Roles.Authenticated.value)


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPlanPermissionsImport:
    def test_listed_roles_get_exactly_the_listed_permissions(self, test_role):
        perm_model.RolePermission.create("authenticated", "perm_2")
        perm_model.RolePermission.create(test_role["id"], "perm_2")

        plan = utils.plan_permissions_import({"version": 1, "roles": {"authenticated": ["perm_1"]}})

        assert plan.permissions["perm_1"] == {"authenticated": True}
        assert plan.permissions["perm_2"] == {"authenticated": False}
        assert plan.get_changes() == [("perm_1", "authenticated", True), ("perm_2", "authenticated", False)]

    def test_unknown_roles_and_permissions_are_skipped(self):
        plan = utils.plan_permissions_import(
            {"version": 1, "roles": {"missing": ["perm_1"], "authenticated": ["perm_1", "removed_permission"]}}
        )

        assert plan.unknown_roles == ["missing"]
        assert plan.unknown_permissions == ["removed_permission"]
        assert all("missing" not in roles for roles in plan.permissions.values())
        assert "removed_permission" not in plan.permissions

    def test_blocked_grants_are_skipped(self):
        plan = utils.plan_permissions_import(
            {"version": 1, "roles": {"anonymous": ["read_any_dataset", "update_any_dataset"]}}
        )

        assert plan.blocked == [("update_any_dataset", "anonymous")]
        assert plan.permissions["read_any_dataset"]["anonymous"] is True
        assert plan.permissions["update_any_dataset"]["anonymous"] is False

    def test_matching_permissions_have_no_changes(self):
        perm_model.RolePermission.create("authenticated", "perm_1")

        assert not utils.plan_permissions_import(utils.export_permissions()).get_changes()

    @pytest.mark.parametrize(
        ("data", "message"),
        [
            ([], "must be a JSON object"),
            ({"roles": {}}, "Unsupported export version"),
            ({"version": 2, "roles": {}}, "Unsupported export version"),
            ({"version": 1}, "must map each role"),
            ({"version": 1, "roles": {"authenticated": "perm_1"}}, "must map each role"),
            ({"version": 1, "roles": {"authenticated": [1]}}, "must map each role"),
        ],
    )
    def test_invalid_export(self, data, message):
        with pytest.raises(tk.ValidationError, match=message):
            utils.plan_permissions_import(data)

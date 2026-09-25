from collections.abc import Callable
from typing import Any

import pytest

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.tests.helpers import call_action, call_auth

from ckanext.permissions import const, utils


def _with_dependencies(permission: str) -> list[str]:
    permissions = [permission]

    for dependency in utils.get_permission_dependencies(permission):
        permissions.extend(_with_dependencies(dependency))

    return permissions


def _grant(permission: str, role_id: str) -> None:
    call_action("permissions_update", permissions={key: {role_id: True} for key in _with_dependencies(permission)})


@pytest.fixture
def org_scoped_user(
    user_factory: Callable[..., dict[str, Any]],
    organization_factory: Callable[..., dict[str, Any]],
    test_role: dict[str, Any],
) -> Callable[[str], tuple[dict[str, Any], dict[str, Any]]]:
    """Create a user whose role grants the permission only in one organization."""

    def factory(permission: str) -> tuple[dict[str, Any], dict[str, Any]]:
        user = user_factory()
        org = organization_factory()

        _grant(permission, test_role["id"])
        utils.assign_role_to_user(user["id"], test_role["id"], const.SCOPE_ORGANIZATION, org["id"])

        return user, org

    return factory


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestOrganizationScopedAuth:
    def test_read_private_dataset(self, org_scoped_user, dataset_factory, organization_factory):
        user, org = org_scoped_user("read_private_dataset")
        dataset = dataset_factory(owner_org=org["id"], private=True)
        other_dataset = dataset_factory(owner_org=organization_factory()["id"], private=True)

        context = {"user": user["name"], "package": model.Package.get(dataset["id"])}
        assert call_auth("package_show", context, id=dataset["id"])

        context = {"user": user["name"], "package": model.Package.get(other_dataset["id"])}
        with pytest.raises(tk.NotAuthorized):
            call_auth("package_show", context, id=other_dataset["id"])

    @pytest.mark.parametrize(
        ("auth", "permission"),
        [("package_update", "update_any_dataset"), ("package_delete", "delete_any_dataset")],
    )
    def test_dataset_write(self, org_scoped_user, dataset_factory, organization_factory, auth, permission):
        user, org = org_scoped_user(permission)
        dataset = dataset_factory(owner_org=org["id"])
        other_dataset = dataset_factory(owner_org=organization_factory()["id"])

        assert call_auth(auth, {"user": user["name"]}, id=dataset["id"])

        with pytest.raises(tk.NotAuthorized):
            call_auth(auth, {"user": user["name"]}, id=other_dataset["id"])

    def test_resource_delete(self, org_scoped_user, dataset_factory, organization_factory, resource_factory):
        user, org = org_scoped_user("delete_any_resource")
        resource = resource_factory(package_id=dataset_factory(owner_org=org["id"])["id"])
        other_resource = resource_factory(package_id=dataset_factory(owner_org=organization_factory()["id"])["id"])

        assert call_auth("resource_delete", {"user": user["name"]}, id=resource["id"])

        with pytest.raises(tk.NotAuthorized):
            call_auth("resource_delete", {"user": user["name"]}, id=other_resource["id"])


@pytest.fixture
def global_user(
    user_factory: Callable[..., dict[str, Any]], test_role: dict[str, Any]
) -> Callable[[str], dict[str, Any]]:
    """Create a user whose global role grants the permission."""

    def factory(permission: str) -> dict[str, Any]:
        user = user_factory()

        _grant(permission, test_role["id"])
        utils.assign_role_to_user(user["id"], test_role["id"])

        return user

    return factory


def _call_dataset_auth(auth: str, user_name: str, dataset: dict[str, Any], resource: dict[str, Any]) -> None:
    if auth == "package_show":
        call_auth(auth, {"user": user_name, "package": model.Package.get(dataset["id"])}, id=dataset["id"])
    elif auth == "resource_delete":
        call_auth(auth, {"user": user_name}, id=resource["id"])
    else:
        call_auth(auth, {"user": user_name}, id=dataset["id"])


DATASET_AUTH_CASES = [
    ("package_show", "read_any_dataset"),
    ("package_show", "read_private_dataset"),
    ("package_update", "update_any_dataset"),
    ("package_delete", "delete_any_dataset"),
    ("resource_delete", "delete_any_resource"),
]


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestGlobalAuth:
    @pytest.mark.parametrize(("auth", "permission"), DATASET_AUTH_CASES)
    def test_granted_in_any_organization(self, global_user, dataset_factory, resource_factory, auth, permission):
        user = global_user(permission)
        dataset = dataset_factory(private=True)
        resource = resource_factory(package_id=dataset["id"])

        _call_dataset_auth(auth, user["name"], dataset, resource)

    @pytest.mark.parametrize(("auth", "permission"), DATASET_AUTH_CASES)
    def test_denied_without_permission(self, user_factory, dataset_factory, resource_factory, auth, permission):
        user = user_factory()
        dataset = dataset_factory(private=True)
        resource = resource_factory(package_id=dataset["id"])

        with pytest.raises(tk.NotAuthorized):
            _call_dataset_auth(auth, user["name"], dataset, resource)

    def test_resource_delete_action(self, global_user, dataset_factory, resource_factory):
        user = global_user("delete_any_resource")
        resource = resource_factory(package_id=dataset_factory(private=True)["id"])

        call_action("resource_delete", {"user": user["name"], "ignore_auth": False}, id=resource["id"])

        assert model.Resource.get(resource["id"]).state == model.State.DELETED

    def test_anonymous_role(self, dataset_factory):
        dataset = dataset_factory(private=True)
        context = {"user": "", "package": model.Package.get(dataset["id"])}

        with pytest.raises(tk.NotAuthorized):
            call_auth("package_show", context, id=dataset["id"])

        call_action("permissions_update", permissions={"read_private_dataset": {const.Roles.Anonymous.value: True}})

        assert call_auth("package_show", context, id=dataset["id"])


SYSADMIN_ONLY_ACTIONS = [
    ("permission_role_create", {"id": "editor", "label": "Editor", "description": "Editor role"}),
    ("permission_role_update", {"id": "creator", "description": "Updated"}),
    ("permission_role_delete", {"id": "creator"}),
    ("permissions_update", {"permissions": {"perm_1": {"anonymous": True}}}),
]


@pytest.mark.usefixtures("with_plugins", "clean_db", "test_role")
class TestSysadminOnlyActions:
    @pytest.mark.parametrize(("action", "data"), SYSADMIN_ONLY_ACTIONS)
    def test_regular_user_denied(self, user, action, data):
        with pytest.raises(tk.NotAuthorized):
            call_action(action, {"user": user["name"], "ignore_auth": False}, **data)

    @pytest.mark.parametrize(("action", "data"), SYSADMIN_ONLY_ACTIONS)
    def test_sysadmin_allowed(self, sysadmin, action, data):
        call_action(action, {"user": sysadmin["name"], "ignore_auth": False}, **data)


@pytest.mark.usefixtures("with_plugins", "clean_db", "clean_index")
class TestOrganizationScopedSearch:
    def test_private_datasets_visible_only_in_scoped_org(self, org_scoped_user, dataset_factory, organization_factory):
        user, org = org_scoped_user("read_private_dataset")
        dataset = dataset_factory(owner_org=org["id"], private=True)
        dataset_factory(owner_org=organization_factory()["id"], private=True)

        result = call_action(
            "package_search",
            {"user": user["name"], "ignore_auth": False},
            include_private=True,
        )

        assert [pkg["id"] for pkg in result["results"]] == [dataset["id"]]


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestCreateDataset:
    def test_auth_scoped_to_organization(self, org_scoped_user, organization_factory):
        user, org = org_scoped_user("create_dataset")

        assert call_auth("package_create", {"user": user["name"]}, owner_org=org["id"])
        assert call_auth("package_create", {"user": user["name"]})

        with pytest.raises(tk.NotAuthorized):
            call_auth("package_create", {"user": user["name"]}, owner_org=organization_factory()["id"])

    def test_create_action(self, org_scoped_user):
        user, org = org_scoped_user("create_dataset")

        dataset = call_action(
            "package_create", {"user": user["name"], "ignore_auth": False}, name="new-dataset", owner_org=org["name"]
        )

        assert dataset["owner_org"] == org["id"]

    def test_organization_list_for_user(self, org_scoped_user, organization_factory):
        user, org = org_scoped_user("create_dataset")
        organization_factory()

        result = call_action(
            "organization_list_for_user", {"user": user["name"]}, id=user["id"], permission="create_dataset"
        )

        assert [organization["id"] for organization in result] == [org["id"]]


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPurgeDataset:
    def test_scoped_to_organization(self, org_scoped_user, dataset_factory, organization_factory):
        user, org = org_scoped_user("purge_dataset")

        assert call_auth("dataset_purge", {"user": user["name"]}, id=dataset_factory(owner_org=org["id"])["id"])

        with pytest.raises(tk.NotAuthorized):
            call_auth(
                "dataset_purge",
                {"user": user["name"]},
                id=dataset_factory(owner_org=organization_factory()["id"])["id"],
            )


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestManageDatasetCollaborators:
    def test_manage_other_users(self, org_scoped_user, dataset_factory, user_factory):
        user, org = org_scoped_user("manage_dataset_collaborators")
        dataset = dataset_factory(owner_org=org["id"])
        other = user_factory()
        context = {"user": user["name"]}

        assert call_auth("package_collaborator_create", context, id=dataset["id"], user_id=other["id"])
        assert call_auth("package_collaborator_delete", context, id=dataset["id"], user_id=other["id"])
        assert call_auth("package_collaborator_list", context, id=dataset["id"])

    def test_cannot_add_themselves(self, org_scoped_user, dataset_factory):
        user, org = org_scoped_user("manage_dataset_collaborators")
        dataset = dataset_factory(owner_org=org["id"])

        with pytest.raises(tk.NotAuthorized):
            call_auth("package_collaborator_create", {"user": user["name"]}, id=dataset["id"], user_id=user["id"])

    def test_scoped_to_organization(self, org_scoped_user, dataset_factory, organization_factory):
        user, _org = org_scoped_user("manage_dataset_collaborators")
        dataset = dataset_factory(owner_org=organization_factory()["id"])

        with pytest.raises(tk.NotAuthorized):
            call_auth("package_collaborator_list", {"user": user["name"]}, id=dataset["id"])


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestBulkUpdateDatasets:
    @pytest.mark.parametrize("auth", ["bulk_update_private", "bulk_update_public", "bulk_update_delete"])
    def test_scoped_to_organization(self, org_scoped_user, organization_factory, auth):
        user, org = org_scoped_user("bulk_update_datasets")

        assert call_auth(auth, {"user": user["name"]}, org_id=org["id"])
        assert call_auth(auth, {"user": user["name"]}, org_id=org["name"])

        with pytest.raises(tk.NotAuthorized):
            call_auth(auth, {"user": user["name"]}, org_id=organization_factory()["id"])


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestManageOrganizationMembers:
    def test_add_and_remove_member(self, org_scoped_user, user_factory):
        user, org = org_scoped_user("manage_organization_members")
        other = user_factory()
        context = {"user": user["name"], "ignore_auth": False}

        call_action("organization_member_create", context, id=org["id"], username=other["name"], role="editor")
        assert call_auth("group_edit_permissions", {"user": user["name"]}, id=org["id"])

        call_action("organization_member_delete", context, id=org["id"], username=other["name"])

    @pytest.mark.parametrize(("target", "role"), [("other", "admin"), ("self", "editor")])
    def test_cannot_escalate(self, org_scoped_user, user_factory, target, role):
        user, org = org_scoped_user("manage_organization_members")
        username = user["name"] if target == "self" else user_factory()["name"]

        with pytest.raises(tk.NotAuthorized):
            call_action(
                "organization_member_create",
                {"user": user["name"], "ignore_auth": False},
                id=org["id"],
                username=username,
                role=role,
            )

    def test_cannot_remove_admin(self, org_scoped_user, user_factory):
        user, org = org_scoped_user("manage_organization_members")
        admin = user_factory()
        call_action("organization_member_create", id=org["id"], username=admin["name"], role="admin")

        with pytest.raises(tk.NotAuthorized):
            call_action(
                "organization_member_delete",
                {"user": user["name"], "ignore_auth": False},
                id=org["id"],
                username=admin["name"],
            )

    def test_scoped_to_organization(self, org_scoped_user, user_factory, organization_factory):
        user, _org = org_scoped_user("manage_organization_members")

        with pytest.raises(tk.NotAuthorized):
            call_action(
                "organization_member_create",
                {"user": user["name"], "ignore_auth": False},
                id=organization_factory()["id"],
                username=user_factory()["name"],
                role="member",
            )


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestGroupPermissions:
    @pytest.mark.ckan_config("ckan.auth.user_create_organizations", False)
    @pytest.mark.ckan_config("ckan.auth.user_create_groups", False)
    @pytest.mark.parametrize(
        ("auth", "permission"),
        [("organization_create", "create_organization"), ("group_create", "create_group")],
    )
    def test_create(self, global_user, user_factory, auth, permission):
        user = global_user(permission)

        assert call_auth(auth, {"user": user["name"]})

        with pytest.raises(tk.NotAuthorized):
            call_auth(auth, {"user": user_factory()["name"]})

    def test_manage_any_group(self, global_user, group_factory, organization_factory, dataset_factory):
        user = global_user("manage_any_group")
        group = group_factory()
        context = {"user": user["name"]}

        assert call_auth("group_update", context, id=group["id"])
        assert call_auth("member_create", context, id=group["id"], object_type="package")

        with pytest.raises(tk.NotAuthorized):
            call_auth("organization_update", context, id=organization_factory()["id"])

        dataset = dataset_factory()
        call_action(
            "member_create",
            {"user": user["name"], "ignore_auth": False},
            id=group["id"],
            object=dataset["id"],
            object_type="package",
            capacity="public",
        )

        assert [g["id"] for g in call_action("group_list_authz", context)] == [group["id"]]

    def test_org_scoped_role_does_not_grant(self, org_scoped_user, group_factory):
        user, _org = org_scoped_user("manage_any_group")

        with pytest.raises(tk.NotAuthorized):
            call_auth("group_update", {"user": user["name"]}, id=group_factory()["id"])

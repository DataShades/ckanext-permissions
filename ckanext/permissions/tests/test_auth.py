from collections.abc import Callable
from typing import Any

import pytest

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.tests.helpers import call_action, call_auth

from ckanext.permissions import const, utils


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

        call_action("permissions_update", permissions={permission: {test_role["id"]: True}})
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

        call_action("permissions_update", permissions={permission: {test_role["id"]: True}})
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

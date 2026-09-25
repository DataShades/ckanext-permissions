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

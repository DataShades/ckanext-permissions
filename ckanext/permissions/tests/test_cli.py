import pytest

from ckan.cli.cli import ckan

from ckanext.permissions import const
from ckanext.permissions import model as perm_model


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestOrphans:
    def test_nothing_to_report(self, cli):
        result = cli.invoke(ckan, ["permissions", "orphans"])

        assert not result.exit_code, result.output
        assert "No grants of undefined permissions" in result.output

    def test_lists_without_deleting(self, cli):
        perm_model.RolePermission.create(const.Roles.Authenticated.value, "removed_permission")

        result = cli.invoke(ckan, ["permissions", "orphans"])

        assert not result.exit_code, result.output
        assert "removed_permission\tauthenticated" in result.output
        assert perm_model.RolePermission.get(const.Roles.Authenticated.value, "removed_permission")

    def test_delete_keeps_registered_grants(self, cli):
        authenticated = const.Roles.Authenticated.value
        perm_model.RolePermission.create(authenticated, "removed_permission")
        perm_model.RolePermission.create(authenticated, "perm_1")

        result = cli.invoke(ckan, ["permissions", "orphans", "--delete"])

        assert not result.exit_code, result.output
        assert not perm_model.RolePermission.get(authenticated, "removed_permission")
        assert perm_model.RolePermission.get(authenticated, "perm_1")

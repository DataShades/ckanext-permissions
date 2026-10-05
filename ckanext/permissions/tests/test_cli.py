import json
from datetime import datetime, timedelta, timezone

import pytest

from ckan import model
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


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestExportImport:
    def test_export(self, cli):
        perm_model.RolePermission.create(const.Roles.Authenticated.value, "perm_1")

        result = cli.invoke(ckan, ["permissions", "export"])

        assert not result.exit_code, result.output
        assert json.loads(result.stdout)["roles"]["authenticated"] == ["perm_1"]

    def test_import(self, cli):
        perm_model.RolePermission.create(const.Roles.Authenticated.value, "perm_2")
        data = json.dumps({"version": 1, "roles": {"authenticated": ["perm_1"], "missing": []}})

        result = cli.invoke(ckan, ["permissions", "import"], input=data)

        assert not result.exit_code, result.output
        assert "Skipped role missing" in result.output
        assert "+ perm_1\tauthenticated" in result.output
        assert "- perm_2\tauthenticated" in result.output
        assert perm_model.RolePermission.get(const.Roles.Authenticated.value, "perm_1")
        assert not perm_model.RolePermission.get(const.Roles.Authenticated.value, "perm_2")

    def test_import_dry_run(self, cli):
        data = json.dumps({"version": 1, "roles": {"authenticated": ["perm_1"]}})

        result = cli.invoke(ckan, ["permissions", "import", "--dry-run"], input=data)

        assert not result.exit_code, result.output
        assert "+ perm_1\tauthenticated" in result.output
        assert not perm_model.RolePermission.get(const.Roles.Authenticated.value, "perm_1")

    def test_import_export_roundtrip_has_no_changes(self, cli):
        perm_model.RolePermission.create(const.Roles.Authenticated.value, "perm_1")
        exported = cli.invoke(ckan, ["permissions", "export"]).stdout

        result = cli.invoke(ckan, ["permissions", "import"], input=exported)

        assert not result.exit_code, result.output
        assert "Permissions already match" in result.output

    def test_import_reports_broken_dependencies(self, cli):
        data = json.dumps({"version": 1, "roles": {"authenticated": ["update_any_dataset"]}})

        result = cli.invoke(ckan, ["permissions", "import"], input=data)

        assert result.exit_code
        assert "can't have Update any dataset without" in result.output
        assert not perm_model.RolePermission.get(const.Roles.Authenticated.value, "update_any_dataset")

    @pytest.mark.parametrize(
        ("data", "message"),
        [("{", "Invalid JSON"), ('{"version": 2, "roles": {}}', "Unsupported export version")],
    )
    def test_import_invalid(self, cli, data, message):
        result = cli.invoke(ckan, ["permissions", "import"], input=data)

        assert result.exit_code
        assert message in result.output


def _log_entry(days_ago: int) -> str:
    entry = perm_model.ChangeLog.create(const.ChangeAction.RoleCreated, "editor", commit=False)
    entry.timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)
    model.Session.commit()

    return entry.id


def _log_ids() -> set[str]:
    return {entry.id for entry in model.Session.query(perm_model.ChangeLog)}


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPruneChanges:
    def test_deletes_only_old_entries(self, cli):
        _log_entry(400)
        recent = _log_entry(10)

        result = cli.invoke(ckan, ["permissions", "changes", "prune", "--older-than", "365"])

        assert not result.exit_code, result.output
        assert "1 entry(ies) deleted" in result.output
        assert _log_ids() == {recent}

    def test_dry_run_keeps_entries(self, cli):
        old = _log_entry(400)

        result = cli.invoke(ckan, ["permissions", "changes", "prune", "--older-than", "365", "--dry-run"])

        assert not result.exit_code, result.output
        assert "1 entry(ies) older than 365 day(s)" in result.output
        assert _log_ids() == {old}

    def test_nothing_to_prune(self, cli):
        _log_entry(10)

        result = cli.invoke(ckan, ["permissions", "changes", "prune", "--older-than", "365"])

        assert not result.exit_code, result.output
        assert "No change log entries older than 365 day(s)" in result.output

    @pytest.mark.parametrize("args", [[], ["--older-than", "0"]])
    def test_requires_positive_age(self, cli, args):
        entry = _log_entry(400)

        result = cli.invoke(ckan, ["permissions", "changes", "prune", *args])

        assert result.exit_code
        assert _log_ids() == {entry}

from typing import Any

import pytest

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.tests.helpers import call_action

from ckanext.permissions import const
from ckanext.permissions import model as perm_model


def _entries(role_id: str) -> list[perm_model.ChangeLog]:
    return (
        model.Session.query(perm_model.ChangeLog)
        .filter(perm_model.ChangeLog.role_id == role_id)
        .order_by(perm_model.ChangeLog.timestamp)
        .all()
    )


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRoleChangeLog:
    def test_create_is_recorded_with_actor(self, sysadmin):
        call_action(
            "permission_role_create",
            {"user": sysadmin["name"]},
            id="editor",
            label="Editor",
            description="Edits things",
        )

        [entry] = _entries("editor")

        assert entry.action == const.ChangeAction.RoleCreated.value
        assert entry.actor_id == sysadmin["id"]
        assert entry.data == {"label": "Editor", "description": "Edits things"}

    def test_update_records_only_changed_fields(self, test_role: dict[str, Any]):
        call_action("permission_role_update", id=test_role["id"], label="Renamed", description=test_role["description"])

        entry = _entries(test_role["id"])[-1]

        assert entry.action == const.ChangeAction.RoleUpdated.value
        assert entry.data == {"label": "Renamed", "changes": {"label": [test_role["label"], "Renamed"]}}

    def test_update_without_changes_is_not_recorded(self, test_role: dict[str, Any]):
        call_action("permission_role_update", id=test_role["id"], description=test_role["description"])

        assert [entry.action for entry in _entries(test_role["id"])] == [const.ChangeAction.RoleCreated.value]

    def test_delete_keeps_history_of_the_role(self, test_role: dict[str, Any]):
        call_action("permissions_update", permissions={"perm_1": {test_role["id"]: True}})
        call_action("permission_role_delete", id=test_role["id"])

        entries = _entries(test_role["id"])

        assert [entry.action for entry in entries] == [
            const.ChangeAction.RoleCreated.value,
            const.ChangeAction.PermissionGranted.value,
            const.ChangeAction.RoleDeleted.value,
        ]
        assert entries[-1].data["label"] == test_role["label"]
        assert entries[-1].data["permissions"] == ["perm_1"]


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestUserRoleChangeLog:
    def test_assign_and_unassign_are_recorded(self, user, test_role: dict[str, Any]):
        call_action("permission_user_roles_update", user_id=user["id"], roles=[test_role["id"]])

        [assigned] = _entries(test_role["id"])[1:]
        [unassigned] = _entries(const.Roles.Authenticated.value)

        assert assigned.action == const.ChangeAction.RoleAssigned.value
        assert unassigned.action == const.ChangeAction.RoleUnassigned.value
        assert assigned.user_id == unassigned.user_id == user["id"]
        assert assigned.data == {"label": test_role["label"], "user_label": user["fullname"], "scope": "global"}

    def test_unchanged_roles_are_not_recorded(self, user):
        call_action("permission_user_roles_update", user_id=user["id"], roles=[const.Roles.Authenticated.value])

        assert not _entries(const.Roles.Authenticated.value)

    def test_organization_scope_is_recorded(self, user, organization):
        call_action(
            "permission_user_roles_update",
            user_id=user["id"],
            roles=[const.Roles.Administrator.value],
            scope=const.SCOPE_ORGANIZATION,
            scope_id=organization["name"],
        )

        [assigned] = _entries(const.Roles.Administrator.value)

        assert perm_model.UserRole.get(user["id"], const.SCOPE_ORGANIZATION, organization["id"])
        assert assigned.data["scope"] == const.SCOPE_ORGANIZATION
        assert assigned.data["organization_label"] == organization["title"]
        assert not _entries(const.Roles.Authenticated.value)

    def test_unknown_organization_is_rejected(self, user):
        with pytest.raises(tk.ValidationError) as e:
            call_action(
                "permission_user_roles_update",
                user_id=user["id"],
                roles=[const.Roles.Administrator.value],
                scope=const.SCOPE_ORGANIZATION,
                scope_id="missing",
            )

        assert e.value.error_dict["scope_id"] == ["Organization not found"]
        assert not _entries(const.Roles.Administrator.value)


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPermissionChangeLog:
    def test_grant_and_revoke_are_recorded(self):
        call_action("permissions_update", permissions={"perm_1": {"anonymous": True}})
        call_action("permissions_update", permissions={"perm_1": {"anonymous": False, "authenticated": False}})

        entries = _entries(const.Roles.Anonymous.value)

        assert [(entry.action, entry.permission) for entry in entries] == [
            (const.ChangeAction.PermissionGranted.value, "perm_1"),
            (const.ChangeAction.PermissionRevoked.value, "perm_1"),
        ]
        assert entries[0].data["label"] == "Anonymous"
        assert not _entries(const.Roles.Authenticated.value)

    def test_rejected_update_is_not_recorded(self):
        with pytest.raises(tk.ValidationError):
            call_action("permissions_update", permissions={"update_any_dataset": {"authenticated": True}})

        assert not _entries(const.Roles.Authenticated.value)

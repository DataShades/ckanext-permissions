import pytest

import ckan.plugins.toolkit as tk
from ckan.tests.helpers import call_action


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPermissionRoleCreate:
    def test_permission_role_create(self):
        result = call_action(
            "permission_role_create",
            id="admin",
            label="Admin",
            description="Admin role",
        )
        assert result["id"] == "admin"
        assert result["label"] == "Admin"
        assert result["description"] == "Admin role"

    @pytest.mark.parametrize("field", ["id", "label", "description"])
    def test_permission_role_create_missing_required_fields(self, field):
        data = {"id": "admin", "label": "Admin", "description": "Admin role"}
        data.pop(field)

        with pytest.raises(tk.ValidationError) as e:
            call_action("permission_role_create", **data)

        assert e.value.error_dict[field] == ["Missing value"]

    def test_permission_role_create_duplicate_id(self):
        call_action(
            "permission_role_create",
            id="admin",
            label="Admin",
            description="Admin role",
        )

        with pytest.raises(tk.ValidationError) as e:
            call_action(
                "permission_role_create",
                id="admin",
                label="Another Admin",
                description="Another admin role",
            )

        assert e.value.error_dict["id"] == ["Role admin is already exists"]


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPermissionRoleDelete:
    def test_permission_role_delete(self):
        # Create a role first
        call_action(
            "permission_role_create",
            id="custom_role",
            label="Custom Role",
            description="Custom role for testing",
        )

        call_action("permission_role_delete", id="custom_role")

        with pytest.raises(tk.ValidationError) as e:
            call_action("permission_role_delete", id="xxx")

        assert e.value.error_dict["id"] == ["Role xxx doesn't exists"]

    def test_permission_role_delete_missing_id(self):
        with pytest.raises(tk.ValidationError) as e:
            call_action("permission_role_delete")

        assert e.value.error_dict["id"] == ["Missing value"]

    def test_permission_role_delete_nonexistent_role(self):
        with pytest.raises(tk.ValidationError) as e:
            call_action("permission_role_delete", id="xxx")

        assert e.value.error_dict["id"] == ["Role xxx doesn't exists"]

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
                        permissions=[
                            PermissionDefinition(key="xxx", label="", description="xxx")
                        ],
                    )
                }
            )

    def test_allow_empty_permission_description(self):
        validate_groups(
            {
                "new_group": PermissionGroup(
                    name="xxx",
                    description="xxx",
                    permissions=[
                        PermissionDefinition(key="xxx", label="xxx", description="")
                    ],
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
        assert result["perm_1"] == PermissionDefinition(
            key="perm_1", label="Permission 1"
        )


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

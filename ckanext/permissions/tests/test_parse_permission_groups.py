import pytest

import ckan.plugins.toolkit as tk

from ckanext.permissions.types import PermissionDefinition, PermissionGroup
from ckanext.permissions.utils import validate_groups


@pytest.mark.usefixtures("with_plugins")
class TestParsePermissionGroups:
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

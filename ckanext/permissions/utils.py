from __future__ import annotations

import inspect
import os

import yaml

import ckan.plugins.toolkit as tk

import ckanext.permissions.model as perm_model
import ckanext.permissions.types as perm_types


def parse_permission_group_schemas() -> dict[str, perm_types.PermissionGroup]:
    groups = _load_schemas(
        tk.aslist(tk.config.get("ckanext.permissions.permission_groups")), "name"
    )

    validate_groups(groups)

    return groups


def _load_schemas(schemas: list[str], type_field: str):
    result = {}

    for path in schemas:
        schema = _load_schema(path)

        if not schema:
            continue

        result[type_field] = schema

    return result


def _load_schema(path: str):
    """
    Given a path like "ckanext.permissions:default_group.yaml"
    find the second part relative to the import path of the first
    """

    module, file_name = path.split(":", 1)

    try:
        # __import__ has an odd signature
        imp_module = __import__(module, fromlist=[""])
    except ImportError:
        return

    file_path = os.path.join(os.path.dirname(inspect.getfile(imp_module)), file_name)

    if not os.path.exists(file_path):
        return

    with open(file_path) as file:
        return yaml.safe_load(file)


def validate_groups(groups: dict[str, perm_types.PermissionGroup]) -> bool:
    permissions = []

    for group in groups.values():
        assert isinstance(group, dict), "Permission group must be a dictionary"
        assert "name" in group, "Permission group must have a name"
        assert "description" in group, "Permission group must have a description"
        assert "permissions" in group, "Permission group must have permissions"

        for permission in group["permissions"]:
            assert isinstance(permission, dict), "Permission must be a dictionary"
            assert "key" in permission, "Permission must have a key"
            assert "label" in permission, "Permission must have a label"

            if permission["key"] in permissions:
                raise ValueError(f"Permission {permission['key']} is duplicated")

            permissions.append(permission["key"])

    return True


def get_permission_groups() -> list[perm_types.PermissionGroup]:
    from ckanext.permissions.plugin import PermissionsPlugin

    return PermissionsPlugin._permissions_groups  # type: ignore


def get_registered_roles() -> dict[str, str]:
    return {role["id"]: role["label"] for role in perm_model.Role.all()}

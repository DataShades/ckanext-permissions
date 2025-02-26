from __future__ import annotations

from typing import Callable

import pytest

import ckan.plugins.toolkit as tk

from ckanext.permissions.const import ROLE_ID_MAX_LENGTH, Roles
from ckanext.permissions.logic.validators import (
    not_default_role,
    role_doesnt_exists,
    role_exists,
    role_id_validator,
    roles_exists,
)


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRoleDoesntExists:
    def test_role_doesnt_exists_valid(self):
        """Test role_doesnt_exists with non-existent role."""
        assert role_doesnt_exists("new_role")

    def test_role_doesnt_exists_invalid(self, test_role: dict[str, str]):
        """Test role_doesnt_exists with existing role."""
        with pytest.raises(tk.Invalid) as e:
            role_doesnt_exists(test_role["id"])

        assert e.value.error == f"Role {test_role['id']} is already exists"


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRoleExists:
    def test_role_exists_valid(self, test_role: dict[str, str]):
        """Test role_exists with existing role."""
        assert role_exists(test_role["id"]) == test_role["id"]

    def test_role_exists_invalid(self):
        """Test role_exists with non-existent role."""
        role_name = "non_existent_role"
        with pytest.raises(tk.Invalid) as e:
            role_exists(role_name)

        assert e.value.error == f"Role {role_name} doesn't exists"


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRolesExists:
    def test_roles_exists_valid(self, role_factory: Callable[..., dict[str, str]]):
        """Test roles_exists with existing roles."""
        role_names = ["creator", "moderator"]
        for role in role_names:
            role_factory(id=role)

        assert roles_exists(role_names) == role_names

    def test_roles_exists_invalid(self, role_factory: Callable[..., dict[str, str]]):
        """Test roles_exists with non-existent role."""
        role_names = ["creator", "moderator"]
        role_factory(id=role_names[0])

        with pytest.raises(tk.Invalid) as e:
            roles_exists(role_names)

        assert e.value.error == f"Role {role_names[1]} doesn't exists"


class TestRoleIdValidator:
    def test_valid_role_id(self):
        """Test role_id_validator with valid role ID."""
        role_id = "valid-role-id"
        assert role_id_validator(role_id) == role_id

    @pytest.mark.parametrize(
        "invalid_id",
        [
            "A",  # too short
            "a" * (ROLE_ID_MAX_LENGTH + 1),  # too long
            "Invalid",  # uppercase
            "invalid@role",  # invalid character
            "test1",  # invalid character
        ],
    )
    def test_invalid_role_id(self, invalid_id: str):
        """Test role_id_validator with invalid role IDs."""
        with pytest.raises(tk.Invalid):
            role_id_validator(invalid_id)


class TestNotDefaultRole:
    def test_valid_custom_role(self):
        """Test not_default_role with custom role."""
        role_id = "custom-role"
        assert not_default_role(role_id) == role_id

    def test_invalid_default_role(self):
        """Test not_default_role with default role."""
        with pytest.raises(tk.Invalid) as e:
            not_default_role(Roles.Sysadmin.value)

        assert e.value.error == f"Role {Roles.Sysadmin.value} is a default role."

from __future__ import annotations

import factory
import pytest
from faker import Faker
from pytest_factoryboy import register

from ckan.tests import factories

import ckanext.permissions.const as perm_const
import ckanext.permissions.model as perm_model

fake = Faker()


def initiate_default_roles():
    """When the clean_db fixture is used, the migrations won't be reruned,
    so we need to initiate the default roles manually"""

    for role in perm_const.Roles:
        if perm_model.Role.get(role.value):
            continue

        perm_model.Role.create(role.value, role.value, f"Default role for {role.value}")


@pytest.fixture()
def clean_db(reset_db, migrate_db_for):
    reset_db()
    migrate_db_for("permissions")

    initiate_default_roles()


@register(_name="test_role")
class RoleFactory(factories.CKANFactory):
    class Meta:
        model = perm_model.Role
        action = "permission_role_create"

    id = "creator"
    label = "Creator"
    description = factory.LazyFunction(lambda: fake.sentence(nb_words=5))


@register(_name="dataset")
class DatasetFactory(factories.Dataset):
    owner_org = factory.LazyFunction(lambda: OrganizationFactory()["id"])


@register(_name="organization")
class OrganizationFactory(factories.Organization):
    pass


@register(_name="sysadmin")
class SysadminFactory(factories.SysadminWithToken):
    pass


@register(_name="user")
class UserFactory(factories.UserWithToken):
    pass

from __future__ import annotations

import factory
import pytest
from faker import Faker
from pytest_factoryboy import register

from ckan import model
from ckan.tests import factories

import ckanext.permissions.model as perm_model
from ckanext.permissions import const

fake = Faker()

DEFAULT_ROLE_LABELS = {
    const.Roles.Anonymous.value: "Anonymous",
    const.Roles.Authenticated.value: "Authenticated",
    const.Roles.Administrator.value: "Administrator",
}


@pytest.fixture
def clean_db(reset_db, migrate_db_for):
    reset_db()
    migrate_db_for("permissions")

    # After the first reset, `reset_db` only deletes rows and keeps the migration
    # version, so the default roles created by a migration are gone and not recreated.
    for role_id, label in DEFAULT_ROLE_LABELS.items():
        if not perm_model.Role.get(role_id):
            perm_model.Role.create(role_id, label, label, commit=False)

    model.Session.commit()


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

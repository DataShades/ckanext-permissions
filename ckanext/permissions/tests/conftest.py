from __future__ import annotations

import factory
import pytest
from faker import Faker
from pytest_factoryboy import register

from ckan.tests.factories import CKANFactory

import ckanext.permissions.model as perm_model

fake = Faker()


@pytest.fixture()
def clean_db(reset_db, migrate_db_for):
    reset_db()
    migrate_db_for("permissions")


@register(_name="test_role")
class RoleFactory(CKANFactory):
    class Meta:
        model = perm_model.Role
        action = "permission_role_create"

    id = "creator"
    label = "Creator"
    description = factory.LazyFunction(lambda: fake.sentence(nb_words=5))

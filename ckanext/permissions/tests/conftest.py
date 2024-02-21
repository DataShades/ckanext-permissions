import pytest
import factory
from pytest_factoryboy import register
from faker import Faker

from ckan.tests.factories import CKANFactory

import ckanext.permissions.const as perm_const
from ckanext.permissions.model import PermissionGroup

fake = Faker()


@pytest.fixture()
def clean_db(reset_db, migrate_db_for):
    reset_db()
    migrate_db_for("permissions")


@register(_name="permission_group")
class PermissionGroupFactory(CKANFactory):
    class Meta:
        model = PermissionGroup
        action = "permission_group_define"

    name = factory.LazyFunction(fake.name)
    description = factory.LazyFunction(lambda: fake.sentence(nb_words=5))


@register(_name="permission")
class PermissionFactory(CKANFactory):
    class Meta:
        model = PermissionGroup
        action = "permission_define"

    key = factory.LazyFunction(fake.name)
    label = factory.LazyFunction(fake.name)
    description = factory.LazyFunction(lambda: fake.sentence(nb_words=5))
    group = factory.LazyFunction(lambda: PermissionGroupFactory()["name"])
    roles = factory.LazyFunction(
        lambda: [{"role": perm_const.ROLE_ANON, "state": perm_const.STATE_DISALLOW}],
    )
    description = factory.LazyFunction(lambda: fake.sentence(nb_words=5))

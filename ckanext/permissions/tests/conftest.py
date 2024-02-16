import pytest
import factory
from pytest_factoryboy import register
from faker import Faker

from ckan.tests.factories import CKANFactory

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

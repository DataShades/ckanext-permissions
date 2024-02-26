from __future__ import annotations

import factory
import pytest
from faker import Faker
from pytest_factoryboy import register

import ckan.plugins as p
import ckan.plugins.toolkit as tk
import ckan.types as types
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
    class Meta:  # type: ignore
        model = PermissionGroup
        action = "permission_group_define"

    name = factory.LazyFunction(fake.name)
    description = factory.LazyFunction(lambda: fake.sentence(nb_words=5))


@register(_name="permission")
class PermissionFactory(CKANFactory):
    class Meta:  # type: ignore
        model = PermissionGroup
        action = "permission_define"

    key = "permission_test"
    label = factory.LazyFunction(fake.name)
    description = factory.LazyFunction(lambda: fake.sentence(nb_words=5))
    group = factory.LazyFunction(
        lambda: PermissionGroupFactory()["name"]
    )  # type: ignore
    roles = factory.LazyFunction(
        lambda: [{"role": perm_const.ROLE_ANON, "state": perm_const.STATE_DISALLOW}],
    )
    description = factory.LazyFunction(lambda: fake.sentence(nb_words=5))


class PermissionTestPlugin(p.SingletonPlugin):
    # p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)

    permission_auth_called = 0

    @staticmethod
    def permission_test_action(
        context: types.Context, data_dict: types.DataDict
    ) -> types.ActionResult.AnyDict:
        tk.check_access("permission_test", context, data_dict)

        return {"result": 1}

    @staticmethod
    @tk.auth_allow_anonymous_access
    @tk.auth_sysadmins_check
    def permission_test_auth(
        context: types.Context, data_dict: types.DataDict
    ) -> types.AuthResult:
        PermissionTestPlugin.permission_auth_called += 1

        return {"success": True}

    def get_actions(self) -> dict[str, types.Action]:
        return {
            "permission_test": self.permission_test_action,
        }

    def get_auth_functions(self) -> dict[str, types.AuthFunction]:
        return {"permission_test": self.permission_test_auth}

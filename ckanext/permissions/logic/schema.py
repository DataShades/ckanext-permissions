from __future__ import annotations

from ckan import types
from ckan.logic.schema import validator_args

from ckanext.permissions import const as perm_const


@validator_args
def role_create(
    not_empty: types.Validator,
    unicode_safe: types.Validator,
    role_id_validator: types.Validator,
    role_doesnt_exists: types.Validator,
    ignore: types.Validator,
) -> types.Schema:
    return {
        "id": [not_empty, unicode_safe, role_id_validator, role_doesnt_exists],
        "label": [not_empty, unicode_safe],
        "description": [not_empty, unicode_safe],
        "__extras": [ignore],
    }


@validator_args
def role_delete(
    not_empty: types.Validator,
    unicode_safe: types.Validator,
    permission_role_exists: types.Validator,
    not_default_role: types.Validator,
) -> types.Schema:
    return {
        "id": [not_empty, unicode_safe, permission_role_exists, not_default_role],
    }


@validator_args
def role_update(
    not_empty: types.Validator,
    unicode_safe: types.Validator,
    permission_role_exists: types.Validator,
    ignore_missing: types.Validator,
) -> types.Schema:
    return {
        "id": [not_empty, unicode_safe, permission_role_exists],
        "label": [ignore_missing, not_empty, unicode_safe],
        "description": [not_empty, unicode_safe],
    }


@validator_args
def user_roles_update(
    not_empty: types.Validator,
    not_missing: types.Validator,
    ignore_missing: types.Validator,
    unicode_safe: types.Validator,
    user_id_or_name_exists: types.Validator,
    list_of_strings: types.Validator,
    roles_exists: types.Validator,
    default: types.ValidatorFactory,
    one_of: types.ValidatorFactory,
) -> types.Schema:
    return {
        "user_id": [not_empty, unicode_safe, user_id_or_name_exists],
        "roles": [not_missing, list_of_strings, roles_exists],
        "scope": [
            default(perm_const.SCOPE_GLOBAL),
            unicode_safe,
            one_of([perm_const.SCOPE_GLOBAL, perm_const.SCOPE_ORGANIZATION]),
        ],
        "scope_id": [ignore_missing, unicode_safe],
    }


@validator_args
def permissions_update(
    default: types.ValidatorFactory,
    convert_to_json_if_string: types.Validator,
    dict_only: types.Validator,
) -> types.Schema:
    return {
        "permissions": [default("{}"), convert_to_json_if_string, dict_only],
    }


@validator_args
def permission_group_schema(not_empty: types.Validator, unicode_safe: types.Validator) -> types.Schema:
    return {
        "name": [not_empty, unicode_safe],
        "description": [not_empty, unicode_safe],
        "permissions": permission_schema(),
    }


@validator_args
def permission_schema(
    not_empty: types.Validator,
    unicode_safe: types.Validator,
    ignore_missing: types.Validator,
    list_of_strings: types.Validator,
    boolean_validator: types.Validator,
) -> types.Schema:
    return {
        "key": [not_empty, unicode_safe],
        "label": [not_empty, unicode_safe],
        "description": [ignore_missing, unicode_safe],
        "depends_on": [ignore_missing, list_of_strings],
        "anonymous": [ignore_missing, boolean_validator],
    }

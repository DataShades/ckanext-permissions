from __future__ import annotations

from ckan import types
from ckan.logic.schema import validator_args


@validator_args
def role_create(not_empty, unicode_safe, role_id_validator, role_doesnt_exists, ignore) -> types.Schema:
    return {
        "id": [not_empty, unicode_safe, role_id_validator, role_doesnt_exists],
        "label": [not_empty, unicode_safe],
        "description": [not_empty, unicode_safe],
        "__extras": [ignore],
    }


@validator_args
def role_delete(not_empty, unicode_safe, permission_role_exists, not_default_role) -> types.Schema:
    return {
        "id": [not_empty, unicode_safe, permission_role_exists, not_default_role],
    }


@validator_args
def role_update(not_empty, unicode_safe, permission_role_exists) -> types.Schema:
    return {
        "id": [not_empty, unicode_safe, permission_role_exists],
        "description": [not_empty, unicode_safe],
    }


@validator_args
def permissions_update(default, convert_to_json_if_string, dict_only) -> types.Schema:
    return {
        "permissions": [default("{}"), convert_to_json_if_string, dict_only],
    }


@validator_args
def permission_group_schema(not_empty, unicode_safe) -> types.Schema:
    return {
        "name": [not_empty, unicode_safe],
        "description": [not_empty, unicode_safe],
        "permissions": permission_schema(),
    }


@validator_args
def permission_schema(not_empty, unicode_safe, ignore_missing) -> types.Schema:
    return {
        "key": [not_empty, unicode_safe],
        "label": [not_empty, unicode_safe],
        "description": [ignore_missing, unicode_safe],
    }

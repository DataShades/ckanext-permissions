from __future__ import annotations

from typing import Any, Dict

from ckan.logic.schema import validator_args

import ckanext.permissions.const as perm_const

Schema = Dict[str, Any]


@validator_args
def permission_group_define(not_empty, unicode_safe, ignore_empty) -> Schema:
    return {
        "name": [not_empty, unicode_safe],
        "description": [ignore_empty, unicode_safe],
    }


@validator_args
def permission_define(
    not_empty,
    unicode_safe,
    ignore,
    ignore_empty,
    permission_group_exists,
) -> Schema:
    role_schema = permission_role_define()
    role_schema.pop("permission")

    return {
        "key": [not_empty, unicode_safe],
        "label": [ignore_empty, unicode_safe],
        "description": [ignore_empty, unicode_safe],
        "group": [not_empty, unicode_safe, permission_group_exists],
        "roles": role_schema,
        "__extras": [ignore],
    }


@validator_args
def permission_set_roles(not_empty, unicode_safe, ignore, permission_exists) -> Schema:
    role_schema = permission_role_define()
    role_schema.pop("permission")

    return {
        "key": [not_empty, unicode_safe, permission_exists],
        "roles": role_schema,
        "__extras": [ignore],
    }


@validator_args
def permission_unset_roles(
    not_empty, unicode_safe, ignore, permission_exists
) -> Schema:
    role_schema = permission_role_define()
    role_schema.pop("permission")

    return {
        "key": [not_empty, unicode_safe, permission_exists],
        "roles": role_schema,
        "__extras": [ignore],
    }


@validator_args
def permission_role_define(
    not_empty,
    unicode_safe,
    ignore,
    one_of,
    permission_exists,
    permission_role_is_allowed,
) -> Schema:
    return {
        "role": [not_empty, unicode_safe, permission_role_is_allowed],
        "permission": [not_empty, unicode_safe, permission_exists],
        "state": [not_empty, unicode_safe, one_of(perm_const.ROLE_STATES)],
        "__extras": [ignore],
    }

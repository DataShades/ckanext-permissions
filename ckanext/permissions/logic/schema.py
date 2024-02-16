from __future__ import annotations

from typing import Any, Dict

from ckan.logic.schema import validator_args

Schema = Dict[str, Any]


@validator_args
def permission_define(
    not_empty,
    list_of_strings,
    permission_allowed_roles,
    unicode_safe,
    ignore,
    default,
) -> Schema:
    return {
        "key": [not_empty, unicode_safe],
        "roles": [default([]), list_of_strings, permission_allowed_roles],
        "__extras": [ignore],
    }


@validator_args
def permission_set(
    not_empty, list_of_strings, permission_allowed_roles, unicode_safe, ignore
) -> Schema:

    return {
        "key": [not_empty, unicode_safe],
        "roles": [not_empty, list_of_strings, permission_allowed_roles],
        "__extras": [ignore],
    }


def permission_unset() -> Schema:
    return permission_set()

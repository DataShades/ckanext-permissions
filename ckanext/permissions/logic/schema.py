from __future__ import annotations

from ckan import types
from ckan.logic.schema import validator_args


@validator_args
def role_create(
    not_empty, unicode_safe, role_id_validator, role_doesnt_exists
) -> types.Schema:
    return {
        "id": [not_empty, unicode_safe, role_id_validator, role_doesnt_exists],
        "label": [not_empty, unicode_safe],
        "description": [not_empty, unicode_safe],
    }


@validator_args
def role_delete(not_empty, unicode_safe, role_exists, not_default_role) -> types.Schema:
    return {
        "id": [not_empty, unicode_safe, role_exists, not_default_role],
    }

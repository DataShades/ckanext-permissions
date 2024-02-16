from __future__ import annotations

from ckan.types import Context, DataDict, AuthResult
from ckan.logic import validate

from ckanext.permissions import model as perm_model
from ckanext.permissions.logic import schema


@validate(schema.permission_define)
def permission_define(context: Context, data_dict: DataDict) -> AuthResult:
    """Define a permission by a key. Default roles could be provided"""
    return {
        "key": data_dict["key"],
        "roles": perm_model.Permission.define_permission(
            data_dict["key"], data_dict["roles"]
        ),
    }


@validate(schema.permission_set)
def permission_set(context: Context, data_dict: DataDict) -> AuthResult:
    """Set roles for a permission by permission key"""

    return {
        "key": data_dict["key"],
        "roles": perm_model.Permission.set_permission(
            data_dict["key"], data_dict["roles"]
        ),
    }


@validate(schema.permission_unset)
def permission_unset(context: Context, data_dict: DataDict) -> AuthResult:
    """Unset roles for a permission by permission key"""

    return {
        "key": data_dict["key"],
        "roles": perm_model.Permission.unset_permission(
            data_dict["key"], data_dict["roles"]
        ),
    }

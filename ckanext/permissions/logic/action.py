from __future__ import annotations

from ckan.types import Context, DataDict, ActionResult
from ckan.logic import validate

from ckanext.permissions import model as perm_model
from ckanext.permissions import types as perm_types
from ckanext.permissions.logic import schema


# ** PERMISSION GROUP **


@validate(schema.permission_group_define)
def permission_group_define(
    context: Context, data_dict: DataDict
) -> perm_types.PermissionGroup:
    """Define a permission group"""

    return perm_model.PermissionGroup.define(**data_dict).dictize(context)


def permision_group_list(
    context: Context, data_dict: DataDict
) -> list[perm_types.PermissionGroup]:
    return [
        perm_group.dictize(context) for perm_group in perm_model.PermissionGroup.all()
    ]


# ** PERMISSION **


@validate(schema.permission_define)
def permission_define(context: Context, data_dict: DataDict) -> perm_types.Permission:
    """Define a permission by a key. Default roles could be provided"""
    return perm_model.Permission.define_permission(**data_dict).dictize(context)


@validate(schema.permission_set_roles)
def permission_set_roles(
    context: Context, data_dict: DataDict
) -> perm_types.Permission:
    return perm_model.Permission.set_permission_roles(
        data_dict["key"], data_dict["roles"]
    )


@validate(schema.permission_set_roles)
def permission_unset_roles(
    context: Context, data_dict: DataDict
) -> perm_types.Permission:
    return perm_model.Permission.unset_permission_roles(
        data_dict["key"], data_dict["roles"]
    )

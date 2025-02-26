from __future__ import annotations

from ckan.logic import validate
from ckan.types import Context, DataDict

from ckanext.permissions import model as perm_model
from ckanext.permissions import types as perm_types
from ckanext.permissions.logic import schema


@validate(schema.role_create)
def permission_role_create(context: Context, data_dict: DataDict) -> perm_types.Role:
    return perm_model.Role.create(data_dict).dictize(context)


@validate(schema.role_delete)
def permission_role_delete(context: Context, data_dict: DataDict) -> None:
    role = perm_model.Role.get(data_dict["id"])

    if role:
        role.delete()

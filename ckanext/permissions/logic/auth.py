from __future__ import annotations
from typing import Callable

import ckan.plugins.toolkit as tk
import ckan.authz as authz
from ckan.types import Context, DataDict, AuthResult

from ckanext.permissions.utils import check_permission


@tk.chained_auth_function
def organization_show(
    next_func: Callable, context: Context, data_dict: DataDict
) -> AuthResult:
    import ipdb

    ipdb.set_trace()
    return authz.is_authorized("group_show", context, data_dict)

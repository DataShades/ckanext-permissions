from __future__ import annotations

import ckanext.ap_main.collection.base as collection_base
from ckanext.collection.utils import StaticData

import ckanext.permissions.utils as perm_utils


class PermissionsManagerCollection(collection_base.ApCollection):
    pager_template = ""

    SerializerFactory = collection_base.ApHtmxTableSerializer.with_attributes(
        record_template="perm_manager/record.html",
        pager_template="perm_manager/pager.html",
    )

    ColumnsFactory = collection_base.ApColumns.with_attributes(
        names=["permission", "anon", "user", "sysadmin"],
        sortable={},
        labels={
            "permission": "Permission",
            "anon": "Anonymous user",
            "user": "Authenticated user",
            "sysadmin": "Administrator",
        },
        width={"permission": "50%"},
        serializers={},
    )

    DataFactory = StaticData.with_attributes(
        data=perm_utils.get_permission_groups(),
    )

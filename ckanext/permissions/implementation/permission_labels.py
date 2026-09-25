from __future__ import annotations

import ckan.plugins as p
from ckan import model
from ckan.lib.plugins import DefaultPermissionLabels

import ckanext.permissions.const as perm_const
import ckanext.permissions.utils as perm_utils


class PermissionLabels(p.SingletonPlugin, DefaultPermissionLabels):
    p.implements(p.IPermissionLabels)

    def get_dataset_labels(self, dataset_obj: model.Package) -> list[str]:
        labels: list[str] = super().get_dataset_labels(dataset_obj)

        labels.append("permission-allowed")

        if dataset_obj.owner_org:
            labels.append(f"permission-allowed-org:{dataset_obj.owner_org}")

        return labels

    def get_user_dataset_labels(self, user_obj: model.User | None) -> list[str]:
        """Get permission labels for a user.

        Extends the default CKAN permission labels by checking if the user has
        special read permissions (read_any_dataset or read_private_dataset).
        If they do, adds a 'permission-allowed' label that grants access to
        the dataset. Roles scoped to an organization add a
        'permission-allowed-org:<org_id>' label for that organization instead.

        Args:
            user_obj: The user to get labels for. Can be None for anonymous users.

        Returns:
            List of permission labels for this user
        """
        labels: list[str] = super().get_user_dataset_labels(user_obj)  # type: ignore

        user = user_obj or model.AnonymousUser()
        read_permissions = ["read_any_dataset", "read_private_dataset"]

        if any(perm_utils.check_permission(permission, user) for permission in read_permissions):
            labels.append("permission-allowed")

        labels.extend(
            f"permission-allowed-org:{org_id}"
            for org_id in perm_utils.get_permission_scope_ids(read_permissions, user, perm_const.SCOPE_ORGANIZATION)
        )

        return labels

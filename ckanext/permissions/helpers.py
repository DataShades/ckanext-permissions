from __future__ import annotations

import ckanext.permissions.utils as utils


def get_registered_roles() -> dict[str, str]:
    return utils.get_registered_roles()

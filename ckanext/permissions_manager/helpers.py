from ckan.lib import munge

from ckanext.permissions.utils import get_registered_roles


def permission_munge_string(value: str) -> str:
    """Munge a string using CKAN's munge_name function.

    Args:
        value: The string to munge

    Returns:
        The munged string
    """
    return munge.munge_name(value)


def permission_get_registered_roles_options() -> list[dict[str, str]]:
    return [
        {"value": role_id, "text": role_label}
        for role_id, role_label in get_registered_roles().items()
        if role_id not in ("anonymous")
    ]

from enum import Enum

ROLE_ID_MIN_LENGTH = 1
ROLE_ID_MAX_LENGTH = 50
ROLE_ID_PATTERN = r"[a-z_\-]+"

SCOPE_GLOBAL = "global"
SCOPE_ORGANIZATION = "organization"


class Roles(Enum):
    Anonymous = "anonymous"
    Authenticated = "authenticated"
    Administrator = "administrator"

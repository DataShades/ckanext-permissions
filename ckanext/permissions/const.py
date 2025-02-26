from enum import Enum

ROLE_ID_MIN_LENGTH = 1
ROLE_ID_MAX_LENGTH = 50


class Roles(Enum):
    Anonymous = "anonymous"
    User = "user"
    Sysadmin = "sysadmin"

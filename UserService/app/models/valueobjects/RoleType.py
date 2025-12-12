from enum import Enum

class RoleType(str, Enum):
    SYSTEM = "SYSTEM"
    APP = "APP"
    APP_SYSTEM = "APP_SYSTEM"
    SYSTEM_ROOT = "SYSTEM_ROOT"

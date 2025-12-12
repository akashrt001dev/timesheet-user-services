from enum import Enum

class BlockOrDeactivateAction(str, Enum):
    BLOCK = "BLOCK"
    DEACTIVATE = "DEACTIVATE"
    UNBLOCK = "UNBLOCK"
    REACTIVATE = "REACTIVATE"
    DELETE = "DELETE"

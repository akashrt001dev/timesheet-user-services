from enum import Enum

class ContractStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DRAFT = "DRAFT"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"
    ACTIVATION_READY = "ACTIVATION_READY"

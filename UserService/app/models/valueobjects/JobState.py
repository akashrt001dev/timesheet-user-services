from enum import Enum

class JobState(str, Enum):
    CREATED = "CREATED"
    DELETED = "DELETED"

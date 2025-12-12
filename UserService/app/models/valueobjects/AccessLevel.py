from enum import Enum

class AccessLevel(str, Enum):
    USER = "USER"
    ENTITY = "ENTITY"
    SITE = "SITE"
    DEPARTMENT = "DEPARTMENT"

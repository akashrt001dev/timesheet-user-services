"""
Endpoints module for User Management Service FastAPI controllers
Contains all REST API endpoints converted from Java Spring Boot controllers
"""

from . import UserController
from . import AuthController
from . import RoleController
from . import SurrogateController
from . import ScimController
from . import UserClientController

__all__ = [
    "UserController",
    "AuthController", 
    "RoleController",
    "SurrogateController",
    "ScimController",
    "UserClientController"
]

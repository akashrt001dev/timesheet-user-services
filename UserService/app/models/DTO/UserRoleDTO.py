from pydantic import BaseModel, EmailStr
from typing import Set, Optional, TYPE_CHECKING

from ..entity.Role import Role

class UserRoleDTO(BaseModel):
    email: Optional[EmailStr] # Assuming Email value object
    roles: Optional[Set['Role']] = set()
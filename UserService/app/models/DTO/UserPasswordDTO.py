from pydantic import BaseModel
from typing import Optional, TYPE_CHECKING

from ..valueobjects.Password import Password

class UserPasswordDTO(BaseModel):
    userId: Optional[str]
    password: Optional['Password']
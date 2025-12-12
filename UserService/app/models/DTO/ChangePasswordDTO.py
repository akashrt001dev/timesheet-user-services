from pydantic import BaseModel
from typing import Optional, TYPE_CHECKING

from ..valueobjects.Password import Password

class ChangePasswordDTO(BaseModel):
    oldPassword: Optional['Password']
    newPassword: Optional['Password']
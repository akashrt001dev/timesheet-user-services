from pydantic import BaseModel
from typing import Optional, TYPE_CHECKING

from ..valueobjects.Password import Password

class UpdatePasswordDTO(BaseModel):
    uuid: Optional[str]
    password: Optional['Password']
from pydantic import BaseModel
from typing import List, Optional, TYPE_CHECKING

from ..aggregates.root.User import User

class UserListDTO(BaseModel):
    users: Optional[List['User']] = []
    numberOfElements: float = 0.0
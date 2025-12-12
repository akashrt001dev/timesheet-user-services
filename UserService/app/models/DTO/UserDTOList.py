from pydantic import BaseModel
from typing import List, TYPE_CHECKING


from .UserDTO import UserDTO
from ..aggregates.root.User import User

class UserDTOList(BaseModel):
    users: List['UserDTO'] = []

    def to_domain_list(self) -> List['User']:
        from ..aggregates.root.User import User
        
        user_list = []
        for user_dto in self.users:
            user = user_dto.to_domain()
            user_list.append(user)
        return user_list
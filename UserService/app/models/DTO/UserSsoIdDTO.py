from pydantic import BaseModel
from typing import Optional, TYPE_CHECKING

from ..valueobjects.SsoId import SsoId

class UserSsoIdDTO(BaseModel):
    uuid: Optional[str]
    ssoId: Optional['SsoId']
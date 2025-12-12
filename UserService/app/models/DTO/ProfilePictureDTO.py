from pydantic import BaseModel
from typing import Optional, TYPE_CHECKING
from datetime import datetime


from ..entity.ProfilePicture import ProfilePicture
from ..reference_object.File import File
from ..valueobjects.EntityId import EntityId
from ..valueobjects.UserId import UserId

class ProfilePictureDTO(BaseModel):
    id: Optional[str]
    userId: Optional['UserId']
    file: Optional['File']
    entityId: Optional['EntityId'] # Note: In Python, there's no direct @JsonIgnore for models
    createdDate: Optional[datetime]
    lastModifiedDate: Optional[datetime]

    def to_domain(self) -> 'ProfilePicture':
        from ..entity.ProfilePicture import ProfilePicture
        return ProfilePicture(**self.dict())
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..reference_object.File import File
from ..valueobjects.UserId import UserId
from ..valueobjects.EntityId import EntityId

class ProfilePicture(BaseModel):
    id: Optional[str] = None
    userId: Optional[UserId] = None
    file: Optional[File] = None
    entityId: Optional[EntityId] = None
    createdDate: Optional[datetime] = None
    lastModifiedDate: Optional[datetime] = None

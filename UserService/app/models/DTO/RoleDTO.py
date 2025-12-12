from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..valueobjects.RoleType import RoleType

class RoleDTO(BaseModel):
    id: Optional[str] = None
    roleName: Optional[str] = None
    roleDescription: Optional[str] = None
    roleType: Optional[RoleType] = None
    isActive: Optional[bool] = True
    createdDate: Optional[datetime] = None
    lastModifiedDate: Optional[datetime] = None
    tenant: Optional[str] = None

    def to_domain(self):
        from ..entity.Role import Role
        return Role(**self.model_dump(exclude_unset=True))
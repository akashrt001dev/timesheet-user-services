from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..valueobjects.RoleType import RoleType

class Role(BaseModel):
    id: Optional[str] = None
    roleName: Optional[str] = None
    roleDescription: Optional[str] = None
    roleType: Optional[RoleType] = None
    isActive: Optional[bool] = True
    createdDate: Optional[datetime] = None
    lastModifiedDate: Optional[datetime] = None
    tenant: Optional[str] = None
    
    def __hash__(self):
        return hash((self.id, self.roleName))
    
    def __eq__(self, other):
        if not isinstance(other, Role):
            return False
        return self.id == other.id and self.roleName == other.roleName

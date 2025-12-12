from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from ..valueobjects.Member import Member
from ..valueobjects.Tenant import Tenant

class Group(BaseModel):
    id: Optional[str] = None
    displayName: Optional[str] = None
    members: Optional[List[Member]] = None
    resourceType: Optional[str] = None
    tenant: Optional[Tenant] = None
    created: Optional[datetime] = None
    lastModified: Optional[datetime] = None

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..valueobjects.SurrogateUser import SurrogateUser
from ..valueobjects.Tenant import Tenant

class SurrogateLog(BaseModel):
    id: Optional[str] = None
    tenant: Optional[Tenant] = None
    user: Optional[SurrogateUser] = None
    surrogate: Optional[SurrogateUser] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    createdDate: Optional[datetime] = None
    lastModifiedDate: Optional[datetime] = None

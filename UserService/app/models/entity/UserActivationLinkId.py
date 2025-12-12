from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserActivationLinkId(BaseModel):
    id: Optional[str] = None
    userId: Optional[str] = None
    tenantId: Optional[str] = None
    # Support both legacy Java 'hashcode' and Python 'hashedUuid'
    hashedUuid: Optional[str] = Field(None, alias="hashcode")
    # Support both datetime expireTime (python) and legacy int millis linkExpireTime
    expireTime: Optional[datetime] = None
    linkExpireTime: Optional[int] = None

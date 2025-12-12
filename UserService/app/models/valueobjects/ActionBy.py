from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ActionBy(BaseModel):
    # Legacy/simple shape
    id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    # Java-equivalent fields used by service
    actionByUserId: Optional[str] = None
    actionDateTime: Optional[datetime] = None

from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from ..reference_object.User import User

class UserSessions(BaseModel):
    id: Optional[str] = None
    user: Optional[User] = None
    logoutDatetime: Optional[datetime] = None
    loginDatetime: Optional[datetime] = None
    tenant: Optional[str] = None
    avgLoginSession: Optional[timedelta] = None

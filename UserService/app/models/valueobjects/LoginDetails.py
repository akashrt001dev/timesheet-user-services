from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LoginDetails(BaseModel):
    loginDateTime: Optional[datetime] = None
    logoutTime: Optional[datetime] = None

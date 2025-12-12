from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from .SurrogateUser import SurrogateUser

class SurrogateSchedule(BaseModel):
    surrogateLogId: Optional[str] = None
    surrogateFor: Optional[SurrogateUser] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None

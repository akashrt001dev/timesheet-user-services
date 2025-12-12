from pydantic import BaseModel
from typing import Optional
from datetime import date

class PlannedToGoLive(BaseModel):
    date: Optional[date] = None

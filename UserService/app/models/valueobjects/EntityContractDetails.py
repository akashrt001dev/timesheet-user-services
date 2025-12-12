from pydantic import BaseModel
from typing import Optional
from .PlannedToGoLive import PlannedToGoLive

class EntityContractDetails(BaseModel):
    plannedGoLive: Optional[PlannedToGoLive] = None

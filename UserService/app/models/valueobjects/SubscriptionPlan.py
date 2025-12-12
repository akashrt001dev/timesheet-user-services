from pydantic import BaseModel
from typing import Optional
from .PlannedToGoLive import PlannedToGoLive

class SubscriptionPlan(BaseModel):
    plannedToGoLive: Optional[PlannedToGoLive] = None

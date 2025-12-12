from pydantic import BaseModel
from typing import Optional, TYPE_CHECKING
from datetime import datetime

from ..entity.SurrogateLog import SurrogateLog
from ..valueobjects.SurrogateUser import SurrogateUser
from ..valueobjects.Tenant import Tenant

class SurrogateLogDTO(BaseModel):
    tenant: Optional['Tenant']
    user: Optional['SurrogateUser']
    surrogate: Optional['SurrogateUser']
    startDate: Optional[datetime]
    endDate: Optional[datetime]

    def to_domain(self) -> 'SurrogateLog':
        from ..entity.SurrogateLog import SurrogateLog
        return SurrogateLog(**self.dict())
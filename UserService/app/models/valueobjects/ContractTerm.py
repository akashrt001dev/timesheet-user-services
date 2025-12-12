from pydantic import BaseModel
from typing import Optional
from datetime import date

class ContractTerm(BaseModel):
    startDate: Optional[date] = None
    endDate: Optional[date] = None
    effectiveDate: Optional[date] = None
    activationDate: Optional[date] = None

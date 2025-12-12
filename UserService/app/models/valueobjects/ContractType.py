from pydantic import BaseModel
from typing import Optional

class ContractType(BaseModel):
    contractType: Optional[str] = None

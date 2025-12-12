from pydantic import BaseModel
from typing import Optional

class ContractManager(BaseModel):
    userID: Optional[str] = None

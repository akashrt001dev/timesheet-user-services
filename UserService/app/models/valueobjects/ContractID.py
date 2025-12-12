from pydantic import BaseModel
from typing import Optional

class ContractID(BaseModel):
    contractID: Optional[str] = None

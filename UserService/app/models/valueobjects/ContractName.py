from pydantic import BaseModel
from typing import Optional

class ContractName(BaseModel):
    contractName: Optional[str] = None

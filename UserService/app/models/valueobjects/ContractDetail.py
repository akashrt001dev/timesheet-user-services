from pydantic import BaseModel
from typing import Optional
from .ContractTerm import ContractTerm

class ContractDetail(BaseModel):
    contractTerm: Optional[ContractTerm] = None

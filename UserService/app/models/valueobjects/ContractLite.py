from pydantic import BaseModel
from typing import Optional
from .ContractName import ContractName
from .ContractStatus import ContractStatus
from .EntityId import EntityId
from .ContractDetail import ContractDetail

class ContractLite(BaseModel):
    id: Optional[str] = None
    contractName: Optional[ContractName] = None
    contractStatus: Optional[ContractStatus] = None
    tenant: Optional[EntityId] = None
    contractDetail: Optional[ContractDetail] = None

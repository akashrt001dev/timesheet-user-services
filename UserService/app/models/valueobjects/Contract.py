from pydantic import BaseModel
from typing import Optional, List, Set
from ..entity.Role import Role
from .ContractName import ContractName
from .ContractStatus import ContractStatus
from .EntityId import EntityId
from .ContractID import ContractID
from .ContractTerm import ContractTerm
from .Sites import Sites

class Contract(BaseModel):
    id: Optional[str] = None
    contractName: Optional[ContractName] = None
    contractStatus: Optional[ContractStatus] = None
    tenant: Optional[EntityId] = None
    contractID: Optional[ContractID] = None
    contractTerm: Optional[ContractTerm] = None
    isSiteLevelResponsible: bool = False
    isDepartmentLevelResponsible: bool = False
    roles: List[Role] = []
    sites: Optional[Sites] = None

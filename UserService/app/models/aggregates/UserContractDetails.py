from pydantic import BaseModel
from typing import Optional
from .root.User import User
from ..valueobjects.ContractID import ContractID
from ..valueobjects.ContractManager import ContractManager
from ..valueobjects.ContractName import ContractName
from ..valueobjects.ContractType import ContractType

class UserContractDetails(BaseModel):
    user: Optional[User] = None
    contractName: Optional[ContractName] = None
    contractID: Optional[ContractID] = None
    contractManager: Optional[ContractManager] = None
    contractType: Optional[ContractType] = None

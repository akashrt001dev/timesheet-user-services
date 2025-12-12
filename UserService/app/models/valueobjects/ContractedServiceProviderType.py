from pydantic import BaseModel
from typing import Optional

class ContractedServiceProviderType(BaseModel):
    id: Optional[str] = None
    contractedServiceProviderType: Optional[str] = None

from pydantic import BaseModel
from typing import Optional, TYPE_CHECKING


from ..valueobjects.Disclaimer import Disclaimer
from ..valueobjects.EntityName import EntityName
from ..valueobjects.Logo import Logo    

class EntityDTO(BaseModel):
    id: Optional[str]
    subdomain: Optional[str]
    entityName: Optional['EntityName']
    logo: Optional['Logo']
    disclaimer: Optional['Disclaimer']
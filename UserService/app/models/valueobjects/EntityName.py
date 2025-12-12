from pydantic import BaseModel
from typing import Optional

class EntityName(BaseModel):
    entityName: Optional[str] = None

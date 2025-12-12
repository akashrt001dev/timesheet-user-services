from pydantic import BaseModel
from typing import Optional

class EntityId(BaseModel):
    id: Optional[str] = None

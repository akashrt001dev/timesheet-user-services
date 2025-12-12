from pydantic import BaseModel
from typing import Optional

class PartnerId(BaseModel):
    id: Optional[str] = None

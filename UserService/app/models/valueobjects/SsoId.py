from pydantic import BaseModel
from typing import Optional

class SsoId(BaseModel):
    id: Optional[str] = None

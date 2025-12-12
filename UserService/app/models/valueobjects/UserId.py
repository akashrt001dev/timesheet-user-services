from pydantic import BaseModel
from typing import Optional

class UserId(BaseModel):
    id: Optional[str] = None

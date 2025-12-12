from pydantic import BaseModel
from typing import Optional

class Title(BaseModel):
    title: Optional[str] = None
    id: Optional[str] = None

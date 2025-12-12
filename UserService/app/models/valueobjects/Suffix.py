from pydantic import BaseModel
from typing import Optional

class Suffix(BaseModel):
    id: Optional[str] = None
    suffix: Optional[str] = None

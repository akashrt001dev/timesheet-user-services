from pydantic import BaseModel
from typing import Optional

class SiteID(BaseModel):
    id: Optional[str] = None

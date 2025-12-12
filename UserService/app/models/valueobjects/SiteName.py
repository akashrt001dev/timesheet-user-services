from pydantic import BaseModel
from typing import Optional

class SiteName(BaseModel):
    siteName: Optional[str] = None

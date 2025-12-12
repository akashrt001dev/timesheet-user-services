from pydantic import BaseModel
from typing import Optional, List
from ..aggregates.Site import Site

class Sites(BaseModel):
    sites: Optional[List[Site]] = None

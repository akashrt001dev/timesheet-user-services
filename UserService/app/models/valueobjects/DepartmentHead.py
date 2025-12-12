from pydantic import BaseModel
from typing import Optional

class DepartmentHead(BaseModel):
    id: Optional[str] = None

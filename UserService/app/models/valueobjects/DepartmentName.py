from pydantic import BaseModel
from typing import Optional

class DepartmentName(BaseModel):
    name: Optional[str] = None

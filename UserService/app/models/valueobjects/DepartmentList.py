from pydantic import BaseModel
from typing import Optional, List
from ..aggregates.Department import Department

class DepartmentList(BaseModel):
    departments: Optional[List[Department]] = None

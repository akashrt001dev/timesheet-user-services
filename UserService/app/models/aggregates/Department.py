from pydantic import BaseModel
from typing import Optional
from ..valueobjects.EntityId import EntityId
from ..valueobjects.EntityName import EntityName
from ..valueobjects.DepartmentName import DepartmentName
from ..valueobjects.DepartmentHead import DepartmentHead
from ..valueobjects.Title import Title

class Department(BaseModel):
    id: Optional[str] = None
    entityId: Optional[EntityId] = None
    entityName: Optional[EntityName] = None
    departmentName: Optional[DepartmentName] = None
    departmentHead: Optional[DepartmentHead] = None
    departmentResponsibility: Optional[Title] = None

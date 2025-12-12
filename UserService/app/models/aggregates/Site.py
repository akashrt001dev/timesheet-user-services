from pydantic import BaseModel
from typing import Optional, List, Set
from ..entity.Role import Role
from ..valueobjects.DepartmentList import DepartmentList
from ..valueobjects.SiteName import SiteName
from ..valueobjects.Title import Title

class Site(BaseModel):
    id: Optional[str] = None
    siteName: Optional[SiteName] = None
    departmentList: Optional[DepartmentList] = None
    siteResponsibility: Optional[Title] = None
    roles: List[Role] = []

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class RegionNameDTO(BaseModel):
    """Wrapper for region name"""
    regionName: Optional[str] = None


class SiteNameDTO(BaseModel):
    """Wrapper for site name"""
    siteName: Optional[str] = None


class SiteResponsibilityDTO(BaseModel):
    """Site responsibility (title) information"""
    title: Optional[str] = None
    id: Optional[str] = None


class DepartmentListDTO(BaseModel):
    """List of departments for a site"""
    departments: Optional[List[dict]] = Field(default_factory=list)


class RoleResponseDTO(BaseModel):
    """Role information in access scope response"""
    id: Optional[str] = None
    roleName: Optional[str] = None
    roleDescription: Optional[str] = None
    roleType: Optional[str] = None
    rolePerformerTypes: Optional[List[str]] = Field(default_factory=list)


class RegionDTO(BaseModel):
    """Region information with sites"""
    id: Optional[str] = None
    regionName: Optional[RegionNameDTO] = None
    roles: Optional[List[RoleResponseDTO]] = Field(default_factory=list)
    allSitesApplicable: bool = False
    sites: Optional[List['SiteDTO']] = Field(default_factory=list)


class SiteDTO(BaseModel):
    """Site information with departments and responsibilities"""
    id: Optional[str] = None
    siteName: Optional[SiteNameDTO] = None
    departmentList: Optional[DepartmentListDTO] = None
    siteResponsibility: Optional[SiteResponsibilityDTO] = None
    region: Optional[RegionDTO] = None
    roles: Optional[List[RoleResponseDTO]] = Field(default_factory=list)


class AccessScopeDetailDTO(BaseModel):
    """Individual access scope with role and region/site details"""
    role: Optional[RoleResponseDTO] = None
    allRegionsApplicable: bool = False
    regions: Optional[List[RegionDTO]] = Field(default_factory=list)


class AccessScopeResponseDTO(BaseModel):
    """Complete access scope response for a user"""
    roles: Optional[List[RoleResponseDTO]] = Field(default_factory=list)
    accessScopes: Optional[List[AccessScopeDetailDTO]] = Field(default_factory=list)


# Update forward references for recursive models
RegionDTO.model_rebuild()
SiteDTO.model_rebuild()

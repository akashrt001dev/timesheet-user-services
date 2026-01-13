from typing import List, Optional
from pydantic import BaseModel
from copy import deepcopy


# Note: MongoDB documents have '_id' fields which are converted to 'id' fields
# by MongoRepository._convert_objectids_and_ids() before Pydantic validation.

# However, for extra safety and to handle edge cases where _id might be missing,
# we make 'id' optional here.

# -----------------------------
# Supporting Value Objects
# -----------------------------

class DepartmentName(BaseModel):
    name: str


class Department(BaseModel):
    id: Optional[str] = None
    departmentName: DepartmentName


class DepartmentList(BaseModel):
    departments: List[Department] = []


class Role(BaseModel):
    id: Optional[str] = None
    roleName: Optional[str] = None
    roleDescription: Optional[str] = None
    roleType: Optional[str] = None
    rolePerformerTypes: List[str] = []


class SiteName(BaseModel):
    siteName: Optional[str] = None


class SiteResponsibility(BaseModel):
    title: Optional[str] = None
    id: Optional[str] = None


class SiteRegion(BaseModel):
    """Region reference within a Site (to avoid circular dependency with Region class)"""
    id: Optional[str] = None
    regionName: Optional["RegionName"] = None


class Site(BaseModel):
    id: Optional[str] = None
    siteName: Optional[SiteName] = None
    siteResponsibility: Optional[SiteResponsibility] = None
    region: Optional[SiteRegion] = None
    roles: List[Role] = []
    departmentList: Optional[DepartmentList] = None


class RegionName(BaseModel):
    regionName: str


class Region(BaseModel):
    id: Optional[str] = None
    regionName: Optional[RegionName] = None
    roles: List[Role] = []
    allSitesApplicable: bool = False
    sites: List[Site] = []


# -----------------------------
# AccessScope Root
# -----------------------------

class AccessScope(BaseModel):
    roles: List[Role] = []
    allRegionsApplicable: bool = False
    regions: List[Region] = []

    # =========================================================
    # Domain Logic (Spring Boot → Python)
    # =========================================================

    @staticmethod
    def get_department_name_list_by_site_id(site_id: str, regions: List[Region]) -> List[str]:
        if not regions:
            return []

        department_names = []

        for region in regions:
            for site in region.sites:
                if site.id == site_id and site.departmentList:
                    for dept in site.departmentList.departments:
                        department_names.append(dept.departmentName.name)

        return department_names

    @staticmethod
    def get_user_access_scope(user) -> List["AccessScopeDTO"]:
        if user.accessScope:
            return AccessScope._process_user_access_scope(user.accessScope)
        return []

    # -----------------------------
    # Internal processing
    # -----------------------------

    @staticmethod
    def _process_user_access_scope(access_scope: "AccessScope"):
        access_scope_dtos: List[AccessScopeDTO] = []

        if access_scope.allRegionsApplicable:
            AccessScope._process_all_region_access(access_scope_dtos, access_scope)
        else:
            AccessScope._process_region_specific_access(access_scope_dtos, access_scope)

        return access_scope_dtos

    @staticmethod
    def _process_all_region_access(dtos, access_scope):
        for role in access_scope.roles:
            AccessScope._add_or_merge_access_scope(
                dtos, role, True, []
            )

    @staticmethod
    def _process_region_specific_access(dtos, access_scope):
        for region in access_scope.regions:
            if region.roles:
                AccessScope._process_region_level_access(dtos, region)
            elif region.sites:
                AccessScope._process_site_level_access(dtos, region)

    @staticmethod
    def _process_region_level_access(dtos, region):
        for role in region.roles:
            AccessScope._add_or_merge_access_scope(
                dtos, role, False, [region]
            )

    @staticmethod
    def _process_site_level_access(dtos, region):
        for site in region.sites:
            if site.roles:
                for role in site.roles:
                    site_region = AccessScope._create_site_specific_region(region, site)
                    AccessScope._add_or_merge_access_scope(
                        dtos, role, False, [site_region]
                    )

    # -----------------------------
    # Merge Helpers
    # -----------------------------

    @staticmethod
    def _add_or_merge_access_scope(dtos, role, all_regions, new_regions):
        existing = next(
            (dto for dto in dtos if dto.role.id == role.id), None
        )

        if existing:
            AccessScope._merge_regions(existing, new_regions, all_regions)
        else:
            dtos.append(
                AccessScopeDTO(
                    role=role,
                    allRegionsApplicable=all_regions,
                    regions=deepcopy(new_regions),
                )
            )

    @staticmethod
    def _merge_regions(existing_dto, new_regions, all_regions):
        if all_regions:
            existing_dto.allRegionsApplicable = True

        if existing_dto.allRegionsApplicable:
            existing_dto.regions = []
            return

        for new_region in new_regions:
            existing_region = next(
                (r for r in existing_dto.regions if r.id == new_region.id), None
            )
            if existing_region:
                AccessScope._merge_sites(existing_region, new_region)
            else:
                existing_dto.regions.append(new_region)

    @staticmethod
    def _merge_sites(existing_region, new_region):
        if new_region.allSitesApplicable:
            existing_region.allSitesApplicable = True

        if existing_region.allSitesApplicable:
            existing_region.sites = []
            return

        for new_site in new_region.sites:
            existing_site = next(
                (s for s in existing_region.sites if s.id == new_site.id), None
            )
            if existing_site:
                AccessScope._merge_roles(existing_site, new_site)
                AccessScope._merge_departments(existing_site, new_site)
            else:
                existing_region.sites.append(new_site)

    @staticmethod
    def _merge_roles(existing_site, new_site):
        existing_role_ids = {r.id for r in existing_site.roles}
        for role in new_site.roles:
            if role.id not in existing_role_ids:
                existing_site.roles.append(role)

    @staticmethod
    def _merge_departments(existing_site, new_site):
        if not new_site.departmentList:
            return

        if not existing_site.departmentList:
            existing_site.departmentList = new_site.departmentList
            return

        existing_ids = {
            d.id for d in existing_site.departmentList.departments
        }

        for dept in new_site.departmentList.departments:
            if dept.id not in existing_ids:
                existing_site.departmentList.departments.append(dept)

    @staticmethod
    def _create_site_specific_region(parent_region, site):
        return Region(
            id=parent_region.id,
            regionName=parent_region.regionName,
            roles=[],
            allSitesApplicable=False,
            sites=[site],
        )


# -----------------------------
# DTO (equivalent to AccessScopeDTO)
# -----------------------------

class AccessScopeDTO(BaseModel):
    role: Role
    allRegionsApplicable: bool = False
    regions: List[Region] = []

from typing import List, Optional
from app.core.constants import AppConstants
from app.models.entity.Role import Role
from app.models.DTO.RoleDTO import RoleDTO
from app.repositories.RoleRepository import RoleRepository
from datetime import datetime, timezone

class RoleService:
    def __init__(self, roleRepository: RoleRepository):
        self.roleRepository = roleRepository

    async def addRole(self, role: Role) -> Role:
        return await self.roleRepository.create(role)

    async def getRolesByType(self, roleTypes: Optional[List[str]]) -> List[Role]:
        if roleTypes:
            return await self.roleRepository.findByRoleTypes(roleTypes)
        else:
            # Using find_all method from MongoRepository base class
            return await self.roleRepository.find_all()

    async def getRolesByName(self, roleName: str) -> List[Role]:
        role_names_to_search = []
        
        scim_map = {
            AppConstants.SCIM_PROXY: [AppConstants.ACTIVITY_LOGGER],
            AppConstants.SCIM_ACTIVITY_LOGGER: [AppConstants.ACTIVITY_LOGGER],
            AppConstants.SCIM_REVIEWER: [AppConstants.REVIEWER, AppConstants.APPROVER],
            AppConstants.SCIM_APPROVER: [AppConstants.FINANCE_REVIEWER_APPROVER],
            AppConstants.SCIM_SYSTEM_ADMIN: [AppConstants.ENTITY_SYS_ADMIN]
        }
        
        if roleName in scim_map:
            role_names_to_search.extend(scim_map[roleName])
        
        if not role_names_to_search:
            return []
            
        return await self.roleRepository.findByRoleNames(role_names_to_search)
    
    # ===== CAMELCASE METHODS TO MATCH JAVA CONTROLLER =====
    
    async def createNewRole(self, roleDTO: RoleDTO) -> Role:
        """
        Create new role - matches Java RoleController.createNewRole
        Java: public Role createNewRole(@RequestBody RoleDTO roleDTO)
        """
        # Map DTO to entity and set Java-like defaults/fields
        now = datetime.now(timezone.utc)
        role = roleDTO.to_domain()
        if role.createdDate is None:
            role.createdDate = now
        if role.lastModifiedDate is None:
            role.lastModifiedDate = None
        if role.isActive is None:
            role.isActive = True
        return await self.addRole(role)
    
    async def getRoles(self, roleTypes: Optional[List[str]] = None) -> List[Role]:
        """
        Get roles with optional type filter - matches Java RoleController.getRoles
        Java: public List<Role> getRoles(@RequestParam(name = "roleType", required = false) List<String> roleTypes)
        """
        return await self.getRolesByType(roleTypes)
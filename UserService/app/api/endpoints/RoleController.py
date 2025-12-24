from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from typing import List, Optional
from app.models.DTO.RoleDTO import RoleDTO
from app.models.entity.Role import Role
from app.services.RoleService import RoleService

router = APIRouter(prefix="/roles")

# Remove the global instance approach and use direct dependency injection
async def get_role_service_dep():
    """FastAPI dependency for RoleService"""
    from app.dependencies import get_role_service
    return await get_role_service()

@router.post("/")
async def createNewRole(
    roleDTO: RoleDTO,
    # X_Authorization: str = Header(alias="X-Authorization"),
    roleService: RoleService = Depends(get_role_service_dep)
) -> Role:
    """
    Equivalent to Java: @PostMapping
    public Role createNewRole(@RequestBody RoleDTO roleDTO)
    """
    try:
        return await roleService.createNewRole(roleDTO)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("")
async def getRoles(
    # X_Authorization: str = Header(alias="X-Authorization"),
    roleType: Optional[List[str]] = Query(None),
    roleService: RoleService = Depends(get_role_service_dep)
) -> List[Role]:
    """
    Equivalent to Java: @GetMapping
    public List<Role> getRoles(@RequestParam(name = "roleType", required = false) List<String> roleTypes)
    """
    try:
        return await roleService.getRoles(roleType)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

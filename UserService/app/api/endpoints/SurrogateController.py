from fastapi import APIRouter, Depends, HTTPException, Header, Path, status
from typing import List, Optional
from app.models.DTO.SurrogateLogDTO import SurrogateLogDTO
from app.models.entity.SurrogateLog import SurrogateLog
from app.models.valueobjects.SurrogateUser import SurrogateUser
from app.services.SurrogateService import SurrogateService

router = APIRouter(prefix="/surrogate")

class SurrogateController:
    """
    Python equivalent of Java SurrogateController
    FastAPI router for surrogate management endpoints
    """
    
    def __init__(self, surrogateService: SurrogateService):
        self.surrogateService = surrogateService

# Create router instance
surrogate_controller = None

def get_surrogate_controller() -> SurrogateController:
    global surrogate_controller
    if surrogate_controller is None:
        # This would be injected via dependency injection in a real app
        from app.dependencies import get_surrogate_service
        surrogate_controller = SurrogateController(get_surrogate_service())
    return surrogate_controller

@router.post("/assign")
async def assignSurrogate(
    surrogateDTO: SurrogateLogDTO,
    X_Authorization: str = Header(alias="X-Authorization"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: SurrogateController = Depends(get_surrogate_controller)
) -> SurrogateLog:
    """
    Equivalent to Java: @PostMapping("/assign")
    public ResponseEntity<?> assignSurrogate(@RequestHeader(value = "X-tenantID") String tenantId, @RequestBody SurrogateLogDTO surrogateDTO)
    """
    try:
        result = await controller.surrogateService.assignSurrogate(X_tenantID, surrogateDTO, None, False)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/{userId}/assign/{surrogateId}")
async def updateAssignedSurrogate(
    surrogateDTO: SurrogateLogDTO,
    surrogateId: str = Path(alias="surrogateId"),
    userId: str = Path(alias="userId"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: SurrogateController = Depends(get_surrogate_controller)
) -> SurrogateLog:
    """
    Equivalent to Java: @PutMapping("/{userId}/assign/{surrogateId}")
    public ResponseEntity<?> updateAssignedSurrogate(@PathVariable("surrogateId") String id, @RequestHeader(value = "X-tenantID") String tenantId, @RequestBody SurrogateLogDTO surrogateDTO)
    """
    try:
        result = await controller.surrogateService.assignSurrogate(X_tenantID, surrogateDTO, surrogateId, True)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/{userId}/unassign/{surrogateId}")
async def unAssignSurrogate(
    surrogateId: str = Path(alias="surrogateId"),
    userId: str = Path(alias="userId"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: SurrogateController = Depends(get_surrogate_controller)
):
    """
    Equivalent to Java: @PutMapping("/{userId}/unassign/{surrogateId}")
    public ResponseEntity<?> unAssignSurrogate(@PathVariable("surrogateId") String id, @RequestHeader(value = "X-tenantID") String tenantId)
    """
    try:
        await controller.surrogateService.unassignSurrogate(X_tenantID, surrogateId)
        return {"status": "accepted"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{userId}")
async def getAllTimeHolders(
    userId: str = Path(alias="userId"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: SurrogateController = Depends(get_surrogate_controller)
) -> List[SurrogateLog]:
    """
    Equivalent to Java: @GetMapping("/{userId}")
    public List<SurrogateLog> getAllTimeHolders(@PathVariable("userId") String issuerId, @RequestHeader(value = "X-tenantID") String tenantId)
    """
    try:
        return await controller.surrogateService.getAllTimeHoldersForIssuer(X_tenantID, userId)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{userId}/active")
async def getCurrentHolders(
    userId: str = Path(alias="userId"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: SurrogateController = Depends(get_surrogate_controller)
) -> List[SurrogateLog]:
    """
    Equivalent to Java: @GetMapping("/{userId}/active")
    public List<SurrogateLog> getCurrentHolders(@PathVariable("userId") String issuerId, @RequestHeader(value = "X-tenantID") String tenantId)
    """
    try:
        return await controller.surrogateService.getCurrentHoldersForIssuer(X_tenantID, userId)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{userId}/surrogateFor")
async def getIssuersForHolder(
    userId: str = Path(alias="userId"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: SurrogateController = Depends(get_surrogate_controller)
) -> List[SurrogateUser]:
    """
    Equivalent to Java: @GetMapping("/{userId}/surrogateFor")
    public List<SurrogateUser> getIssuersForHolder(@PathVariable("userId") String holderId, @RequestHeader(value = "X-tenantID") String tenantId)
    """
    try:
        return await controller.surrogateService.getIssuersForHolder(X_tenantID, userId)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

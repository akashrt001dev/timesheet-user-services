from fastapi import APIRouter, Depends, HTTPException, Request, Response, Path, status
from typing import Dict, Any, Optional
import json
from app.services.UserService import UserService
from app.scim.ScimAuthentication import ScimAuthentication
from app.scim.ScimContext import ScimContext
from app.scim.ResourceEndpoint import ResourceEndpoint
from app.scim.UserHandler import UserHandler
from app.scim.GroupHandler import GroupHandler

router = APIRouter(prefix="/realms/{realm}/scim/v2")

class ScimController:
    """
    Python equivalent of Java ScimController
    Exact translation of the Java @RestController implementation
    """
    
    def __init__(
        self,
        resourceEndpoint: ResourceEndpoint,
        userService: UserService
    ):
        self.resourceEndpoint = resourceEndpoint
        self.userService = userService

# Create router instance
scim_controller = None

def get_scim_controller() -> ScimController:
    global scim_controller
    if scim_controller is None:
        # This would be injected via dependency injection in a real app
        from app.dependencies import get_user_service
        userService = get_user_service()
        
        # Create handlers
        userHandler = UserHandler(userService)
        groupHandler = GroupHandler(userService)
        
        # Create resource endpoint
        resourceEndpoint = ResourceEndpoint(userHandler, groupHandler)
        
        scim_controller = ScimController(
            resourceEndpoint,
            userService
        )
    return scim_controller

def getHttpHeaders(request: Request) -> Dict[str, str]:
    """
    Extract HTTP headers from the request and put them into a map.
    Equivalent to Java getHttpHeaders method.
    """
    httpHeaders = {}
    for headerName, headerValue in request.headers.items():
        httpHeaders[headerName] = headerValue
    return httpHeaders

@router.api_route(
    "/{path:path}",
    methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
    response_class=Response
)
async def handleScimRequest(
    request: Request,
    response: Response,
    realm: str = Path(alias="realm"),
    path: str = Path(alias="path"),
    controller: ScimController = Depends(get_scim_controller)
) -> str:
    """
    Equivalent to Java: @RequestMapping(value = "/**", method = {RequestMethod.POST, RequestMethod.GET, RequestMethod.PUT, RequestMethod.PATCH, RequestMethod.DELETE})
    public @ResponseBody String handleScimRequest(HttpServletRequest request, HttpServletResponse response, @PathVariable("realm") String realm, @RequestBody(required = false) String requestBody)
    
    This is an exact translation of the Java implementation
    """
    # Get request body (equivalent to Java @RequestBody)
    requestBody = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body_bytes = await request.body()
        requestBody = body_bytes.decode('utf-8') if body_bytes else None
    
    # Extract HTTP headers (equivalent to Java getHttpHeaders(request))
    httpHeaders = getHttpHeaders(request)
    
    # Build query string (equivalent to Java request.getQueryString())
    query = f"?{request.url.query}" if request.url.query else ""
    
    # Set tenant ID (equivalent to Java userService.getTenantId(realm))
    await controller.userService.getTenantId(realm)
    
    # Create SCIM authentication (equivalent to Java ScimAuthentication scimAuthentication = new ScimAuthentication())
    scimAuthentication = ScimAuthentication()
    
    # Handle SCIM request (equivalent to Java resourceEndpoint.handleRequest(...))
    scimResponse = await controller.resourceEndpoint.handleRequest(
        str(request.url) + query,  # request.getRequestURL() + query
        request.method,            # HttpMethod.valueOf(request.getMethod())
        requestBody,               # requestBody
        httpHeaders,               # httpHeaders
        ScimContext(request, realm, scimAuthentication)  # new Context(scimAuthentication)
    )
    
    # Set response content type (equivalent to Java response.setContentType(HttpHeader.SCIM_CONTENT_TYPE))
    response.headers["Content-Type"] = "application/scim+json"
    
    # Set additional headers from SCIM response (equivalent to Java scimResponse.getHttpHeaders().forEach(response::setHeader))
    if hasattr(scimResponse, 'httpHeaders') and scimResponse.httpHeaders:
        for key, value in scimResponse.httpHeaders.items():
            response.headers[key] = value
    
    # Set status code (equivalent to Java response.setStatus(scimResponse.getHttpStatus()))
    response.status_code = scimResponse.httpStatus
    
    # Clear tenant ID (equivalent to Java userService.setTenantId())
    await controller.userService.setTenantId()
    
    # Return pretty-printed JSON response (equivalent to Java scimResponse.toPrettyString())
    return scimResponse.toPrettyString()

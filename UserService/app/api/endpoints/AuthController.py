from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, status
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
from app.models.aggregates.root.User import User
from app.models.valueobjects.SsoId import SsoId
from app.models.response.AuthResponse import AuthResponse
from app.services.UserService import UserService
from app.security.JwtUserDetailService import JwtUserDetailService
from app.security.JwtUtil import JwtUtil


router = APIRouter(prefix="/auth")

# Remove the global instance approach and use direct dependency injection
async def get_user_service_dep():
    """FastAPI dependency for UserService"""
    from app.dependencies import get_user_service
    return await get_user_service()

async def get_jwt_user_detail_service_dep():
    """FastAPI dependency for JwtUserDetailService"""
    from app.dependencies import get_jwt_user_detail_service
    return await get_jwt_user_detail_service()

async def get_jwt_util_dep():
    """FastAPI dependency for JwtUtil"""
    from app.dependencies import get_jwt_util
    return await get_jwt_util()

@router.get("/login")
async def login(
    request: Request,
    auth_header: str = Header(..., alias="Authorization", description="Bearer token for authentication", example="Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6..."),
    x_tenant_id: str = Header(..., alias="X-tenantID", description="Tenant ID"),
    userService: UserService = Depends(get_user_service_dep),
    userDetailService: JwtUserDetailService = Depends(get_jwt_user_detail_service_dep),
    jwtUtil: JwtUtil = Depends(get_jwt_util_dep)
):
    """
    Equivalent to Java: @GetMapping("/login")
    public ResponseEntity<?> login(@RequestHeader(value = "Authorization") String authorization, @RequestHeader(value = "X-tenantID") String tenantId, @RequestHeader HttpHeaders headers)
    """
    try:
        # Extract headers similar to Java HttpHeaders
        headers_dict = dict(request.headers)

        # Debug: Log received headers and parameters
        print(f"DEBUG: Received authorization token: {auth_header}")
        print(f"DEBUG: Received x_tenant_id parameter: {x_tenant_id}")
        print(f"DEBUG: All headers: {headers_dict}")

        userName = await userService.extractUserNameFromOauthJwtToken(auth_header, headers_dict)

        if userName:
            user = await userService.getOrCreateUser(userName, x_tenant_id)

            authResponse = await userDetailService.createJwtToken(user, x_tenant_id)
            accessToken = authResponse.accessToken
            ssoId = jwtUtil.getUserEmailFromToken(accessToken)
            userID = jwtUtil.getUserIdFromToken(accessToken)
            _ssoId = SsoId(id=ssoId)

            await userService.saveLoginDateTime(_ssoId, x_tenant_id)

            avgLoginCount = await userService.getUserAvgLoginCount(userID)
            avgLoginSession = await userService.getUserAvgLoginSession(userID)
            await userService.saveLoginDetail(_ssoId, avgLoginCount, avgLoginSession)

            return JSONResponse(content=authResponse.dict(), status_code=202)
        else:
            return JSONResponse(
                content={"error": f"Unable to Fetch User from Auth Token: {auth_header}"},
                status_code=400
            )

    except HTTPException as e:
        # Propagate HTTPException status codes (e.g., 401 on token errors)
        return JSONResponse(content={"error": f"{e.status_code}: {e.detail}"}, status_code=e.status_code)
    except ValueError as e:  # InvalidUserTenantException equivalent
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:  # UsernameNotFoundException, AccountLockedException equivalent
        if "not found" in str(e).lower():
            return JSONResponse(content={"error": str(e)}, status_code=404)
        elif "locked" in str(e).lower():
            return JSONResponse(content={"error": str(e)}, status_code=403)
        else:
            return JSONResponse(content={"error": str(e)}, status_code=400)

@router.post("/logout")
async def logout(
    x_authorization: str = Header(..., alias="X-Authorization"),
    x_tenant_id: str = Header(..., alias="X-tenantID"),
    userDetailService: JwtUserDetailService = Depends(get_jwt_user_detail_service_dep),
    jwtUtil: JwtUtil = Depends(get_jwt_util_dep)
):
    """
    Equivalent to Java: @PostMapping("/logout")
    public ResponseEntity<?> logout(@RequestHeader(value = "X-Authorization") String authorization, @RequestHeader(value = "X-tenantID") String tenantId)
    """
    try:
        userSessionID = jwtUtil.getUserSessionID(x_authorization)
        await userDetailService.setUserSessionLogoutTime(userSessionID)
        
        return JSONResponse(
            content={"message": "You have successfully logged out!"},
            status_code=202
        )
        
    except ValueError as e:  # InvalidUserTenantException equivalent
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:  # UsernameNotFoundException equivalent
        if "not found" in str(e).lower():
            return JSONResponse(content={"error": str(e)}, status_code=404)
        else:
            return JSONResponse(content={"error": str(e)}, status_code=400)

@router.get("/surrogate/login")
async def getAuthResponseForSurrogateUser(
    request: Request,
    auth_header: str = Header(..., alias="Authorization", description="Bearer token for authentication"),
    x_tenant_id: str = Header(..., alias="X-tenantID"),
    userId: str = Query(alias="userId"),
    userService: UserService = Depends(get_user_service_dep),
    userDetailService: JwtUserDetailService = Depends(get_jwt_user_detail_service_dep)
):
    """
    Equivalent to Java: @GetMapping("/surrogate/login")
    public ResponseEntity<?> getAuthResponseForSurrogateUser(...)
    """
    try:
        # Extract headers similar to Java HttpHeaders
        headers = dict(request.headers)
        userName = await userService.extractUserNameFromOauthJwtToken(auth_header, headers)

        if userName:
            user = await userService.getSurrogateForUser(userId, x_tenant_id)
            authResponse = await userDetailService.createJwtToken(user, x_tenant_id)
            return JSONResponse(content=authResponse.dict(), status_code=202)
        else:
            return JSONResponse(
                content={"error": f"Unable to Fetch User from Auth Token: {auth_header}"},
                status_code=400
            )

    except ValueError as e:  # InvalidUserTenantException equivalent
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:  # UsernameNotFoundException, AccountLockedException equivalent
        if "not found" in str(e).lower():
            return JSONResponse(content={"error": str(e)}, status_code=404)
        elif "locked" in str(e).lower():
            return JSONResponse(content={"error": str(e)}, status_code=403)
        else:
            return JSONResponse(content={"error": str(e)}, status_code=400)

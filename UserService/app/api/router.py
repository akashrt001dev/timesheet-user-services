from fastapi import APIRouter
from .endpoints import UserController, AuthController, RoleController, SurrogateController, ScimController,UserClientController

api_router = APIRouter()

# Include all controller routers
api_router.include_router(UserController.router, tags=["User-controller"])
api_router.include_router(AuthController.router, tags=["Authentication-controller"])
api_router.include_router(RoleController.router,tags=["Role-controller"])
api_router.include_router(SurrogateController.router, tags=["Surrogate-controller"])
api_router.include_router(ScimController.router, tags=["SCIM-controller"])
api_router.include_router(UserClientController.router, tags=["User-client-controller"])
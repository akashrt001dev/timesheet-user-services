from fastapi import APIRouter
from .endpoints import UserController, AuthController, RoleController, SurrogateController, ScimController

api_router = APIRouter()

# Include all controller routers
api_router.include_router(UserController.router, tags=["User"])
api_router.include_router(AuthController.router, tags=["Authentication"])
api_router.include_router(RoleController.router,tags=["Role"])
api_router.include_router(SurrogateController.router, tags=["Surrogate"])
api_router.include_router(ScimController.router, tags=["SCIM"])
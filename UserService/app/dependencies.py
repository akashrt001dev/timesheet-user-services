"""
Dependency injection configuration for User Management Service
This file provides dependency injection for FastAPI controllers
equivalent to Spring Boot's @Autowired functionality
"""

from typing import AsyncGenerator
from app.services.UserService import UserService
from app.services.RoleService import RoleService
from app.services.SurrogateService import SurrogateService
from app.security.JwtUtil import JwtUtil
from app.security.OauthJwtDecoder import OauthJwtDecoder
from app.security.SecurityService import SecurityService
from app.repositories.UserRepository import UserRepository
from app.repositories.RoleRepository import RoleRepository
from app.repositories.SurrogateLogRepository import SurrogateLogRepository
from app.repositories.UserSessionRepository import UserSessionRepository
from app.db.mongodb import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.QueryProcessor import QueryProcessor

# Global service instances (in production, use proper DI container)
_user_service = None
_role_service = None
_surrogate_service = None
_jwt_util = None
_security_service = None
_user_repository = None
_role_repository = None
_surrogate_log_repository = None
_user_session_repository = None
_resource_endpoint = None
_oauth_decoder = None

def get_database_dependency() -> AsyncIOMotorDatabase:
    """Get database connection"""
    return get_database()

async def get_user_repository() -> UserRepository:
    """Get UserRepository instance"""
    global _user_repository
    if _user_repository is None:
        db = get_database_dependency()
        _user_repository = UserRepository(db)
    return _user_repository

async def get_role_repository() -> RoleRepository:
    """Get RoleRepository instance"""
    global _role_repository
    if _role_repository is None:
        db = get_database_dependency()
        _role_repository = RoleRepository(db)
    return _role_repository

async def get_surrogate_log_repository() -> SurrogateLogRepository:
    """Get SurrogateLogRepository instance"""
    global _surrogate_log_repository
    if _surrogate_log_repository is None:
        db = get_database_dependency()
        _surrogate_log_repository = SurrogateLogRepository(db)
    return _surrogate_log_repository

async def get_user_session_repository() -> UserSessionRepository:
    """Get UserSessionRepository instance"""
    global _user_session_repository
    if _user_session_repository is None:
        db = get_database_dependency()
        _user_session_repository = UserSessionRepository(db)
    return _user_session_repository

async def get_jwt_util() -> JwtUtil:
    """Get JwtUtil instance"""
    global _jwt_util
    if _jwt_util is None:
        _jwt_util = JwtUtil()
    return _jwt_util

async def get_security_service() -> SecurityService:
    """Get SecurityService instance"""
    global _security_service
    if _security_service is None:
        _security_service = SecurityService()
    return _security_service

async def get_oauth_decoder() -> OauthJwtDecoder:
    """Get OauthJwtDecoder instance"""
    global _oauth_decoder
    if _oauth_decoder is None:
        _oauth_decoder = OauthJwtDecoder()
    return _oauth_decoder

async def get_user_service() -> UserService:
    """Get UserService instance"""
    global _user_service
    if _user_service is None:
        # Get essential dependencies - avoid circular dependency with RoleService
        user_repo = await get_user_repository()
        jwt_util = await get_jwt_util()
        oauth_decoder = await get_oauth_decoder()
        db = get_database_dependency()
        query_processor = QueryProcessor(db, user_repo)

        _user_service = UserService(
            userRepository=user_repo,
            jwtUtil=jwt_util,
            oauthJwtDecoder=oauth_decoder,
            queryProcessor=query_processor,
        )
    return _user_service

async def get_role_service() -> RoleService:
    """Get RoleService instance"""
    global _role_service
    if _role_service is None:
        role_repo = await get_role_repository()
        _role_service = RoleService(role_repo)
    return _role_service

async def get_surrogate_service() -> SurrogateService:
    """Get SurrogateService instance"""
    global _surrogate_service
    if _surrogate_service is None:
        surrogate_repo = await get_surrogate_log_repository()
        user_service = await get_user_service()
        _surrogate_service = SurrogateService(surrogate_repo, user_service)
    return _surrogate_service

async def get_resource_endpoint():
    """Get SCIM ResourceEndpoint instance"""
    global _resource_endpoint
    if _resource_endpoint is None:
        from app.scim.ResourceEndpoint import ResourceEndpoint
        from app.scim.UserHandler import UserHandler
        from app.scim.GroupHandler import GroupHandler
        
        # Get user service
        user_service = await get_user_service()
        
        # Create handlers
        user_handler = UserHandler(user_service)
        group_handler = GroupHandler(user_service)
        
        # Create resource endpoint
        _resource_endpoint = ResourceEndpoint(user_handler, group_handler)
    
    return _resource_endpoint

# FastAPI dependency functions (these would be used with Depends())
def get_user_service_sync() -> UserService:
    """Synchronous version for FastAPI Depends()"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, we need to handle this differently
            # For now, create the service synchronously
            from app.db.mongodb import get_database_sync
            from app.repositories.MongoRepository import MongoRepository
            
            db = get_database_sync()
            user_repo = UserRepository(db)
            return UserService(user_repo)
        else:
            return asyncio.run(get_user_service())
    except:
        # Fallback - create basic instance
        return None

def get_role_service_sync() -> RoleService:
    """Synchronous version for FastAPI Depends()"""
    try:
        import asyncio
        return asyncio.run(get_role_service())
    except:
        return None

def get_surrogate_service_sync() -> SurrogateService:
    """Synchronous version for FastAPI Depends()"""
    try:
        import asyncio
        return asyncio.run(get_surrogate_service())
    except:
        return None

def get_jwt_util_sync() -> JwtUtil:
    """Synchronous version for FastAPI Depends()"""
    return JwtUtil()

def get_security_service_sync() -> SecurityService:
    """Synchronous version for FastAPI Depends()"""
    return SecurityService()

def get_user_repository_sync() -> UserRepository:
    """Synchronous version for FastAPI Depends()"""
    try:
        import asyncio
        return asyncio.run(get_user_repository())
    except:
        return None

from typing import Any

def get_jwt_user_detail_service_sync() -> Any:
    """Deprecated sync provider not used. Present for compatibility."""
    from app.security.JwtUserDetailService import JwtUserDetailService as RealJwtUserDetailService
    # Build minimal real instance
    user_repo = None
    session_repo = None
    jwt_util = JwtUtil()
    return RealJwtUserDetailService(user_repo, session_repo, jwt_util)

# Additional dependency functions for auth components
async def get_jwt_user_detail_service():
    """Get real JwtUserDetailService instance"""
    from app.security.JwtUserDetailService import JwtUserDetailService as RealJwtUserDetailService
    user_repo = await get_user_repository()
    session_repo = await get_user_session_repository()
    jwt_util = await get_jwt_util()
    return RealJwtUserDetailService(user_repo, session_repo, jwt_util)

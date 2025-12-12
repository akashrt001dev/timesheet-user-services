import logging
from datetime import datetime, timedelta
from typing import Optional, Set, Dict, Any
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext

from app.core.constants import AppConstants
from app.models.aggregates.root.User import User
from app.models.entity.UserSessions import UserSessions
from app.models.valueobjects.Email import Email
from app.models.valueobjects.Tenant import Tenant
from app.models.reference_object.User import User as UserRef
from app.repositories.UserRepository import UserRepository
from app.repositories.UserSessionRepository import UserSessionRepository
from app.security.JwtUtil import JwtUtil


class AuthRequest:
    """Authentication request model"""
    def __init__(self, username: str, password: str, tenantId: str):
        self.username = username
        self.password = password
        self.tenantId = tenantId


class AuthResponse:
    """Authentication response model"""
    def __init__(self, accessToken: str, refreshToken: str):
        self.accessToken = accessToken
        self.refreshToken = refreshToken
        
    def dict(self):
        return {
            "accessToken": self.accessToken,
            "refreshToken": self.refreshToken
        }


class UserDetails:
    """Spring Security UserDetails equivalent"""
    def __init__(self, username: str, password: str, authorities: Set[str], 
                 enabled: bool = True, accountNonExpired: bool = True,
                 credentialsNonExpired: bool = True, accountNonLocked: bool = True):
        self.username = username
        self.password = password
        self.authorities = authorities
        self.enabled = enabled
        self.accountNonExpired = accountNonExpired
        self.credentialsNonExpired = credentialsNonExpired
        self.accountNonLocked = accountNonLocked


class InvalidUserTenantException(Exception):
    """Custom exception for invalid user tenant"""
    pass


class AccountLockedException(Exception):
    """Custom exception for locked accounts"""
    pass


class JwtUserDetailService:
    """
    Python equivalent of Java Spring Security UserDetailsService
    Handles JWT authentication, user validation, and session management
    """
    
    def __init__(
        self,
        userRepository: UserRepository,
        userSessionRepository: UserSessionRepository,
        jwtUtil: JwtUtil
    ):
        self.userRepository = userRepository
        self.userSessionRepository = userSessionRepository
        self.jwtUtil = jwtUtil
        self.MAX_ATTEMPTS = 3
        self.LOCKOUT_TIME = 60 * 1000  # 1 minute in milliseconds
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.security = HTTPBearer()
        self.LOG = logging.getLogger(__name__)

    async def createJwtToken(self, user: User, tenantId: str) -> AuthResponse:
        """
        Create JWT token for authenticated user
        Equivalent to Java: createJwtToken(User user, String tenantId)
        """
        try:
            userId = user.id
            
            if await self.isAccountLocked(userId):
                remainingTime = await self.getRemainingLockoutTime(userId)
                raise AccountLockedException(f"Wait for {remainingTime // 1000} seconds")
            
            await self.resetLoginAttempts(userId)
            userSessionObjectId = await self.setUserSession(userId, tenantId)
            
            accessToken = self.jwtUtil.generate(user, "ACCESS", tenantId, userSessionObjectId)
            refreshToken = self.jwtUtil.generate(user, "REFRESH", tenantId, userSessionObjectId)
            
            return AuthResponse(accessToken, refreshToken)
            
        except AccountLockedException:
            raise
        except Exception as e:
            self.LOG.error(f"Error creating JWT token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating authentication token"
            )

    async def loadUserByUsername(self, username: str) -> UserDetails:
        """
        Load user by username for authentication
        Equivalent to Java: loadUserByUsername(String username)
        """
        try:
            email = Email(officialEmail=username)
            user_optional = await self.userRepository.findByEmail(email)
            
            if not user_optional:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Username is not valid"
                )
            
            user = user_optional
            authorities = self._getAuthorities(user)
            
            return UserDetails(
                username=email.officialEmail,
                # Password model serializes to { encryptedPassword: ... } for storage, but internally keep `.password` as hash.
                password=user.password.password if user.password else "",
                authorities=authorities,
                enabled=user.isActivated,
                accountNonLocked=not await self.isAccountLocked(user.id)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.LOG.error(f"Error loading user by username: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error loading user details"
            )

    def _getAuthorities(self, user: User) -> Set[str]:
        """
        Get user authorities/roles
        Equivalent to Java: getAuthorities(User user)
        """
        authorities = set()
        if user.roles:
            for role in user.roles:
                authorities.add(f"ROLE_{role.roleName}")
        return authorities

    async def authenticate(self, userName: str, userPassword: str, userId: Optional[str] = None) -> None:
        """
        Authenticate user credentials
        Equivalent to Java: authenticate(String userName, String userPassword, String userId)
        """
        try:
            user_details = await self.loadUserByUsername(userName)
            
            if not user_details.enabled:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is disabled"
                )
            
            if not user_details.accountNonLocked:
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account is locked"
                )
            
            # Verify password (plain-text comparison per current storage policy)
            if userPassword != user_details.password:
                if userId:
                    await self.incrementLoginAttempts(userId)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Bad credentials from user"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            self.LOG.error(f"Authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    async def checkUserInTenant(self, emailId: str, tenantId: str) -> bool:
        """
        Check if user exists in specific tenant
        Equivalent to Java: checkUserInTenant(String emailId, String tenantId)
        """
        try:
            email = Email(officialEmail=emailId)
            tenant = Tenant(tenantId=tenantId)
            
            user_optional = await self.userRepository.findByEmailAndTenant(email, tenant)
            return user_optional is not None
            
        except Exception as e:
            self.LOG.error(f"Error checking user in tenant: {str(e)}")
            return False

    async def setUserSession(self, userId: str, tenantId: str) -> str:
        """
        Create user session record
        Equivalent to Java: setUserSession(UserSessionRepository userSessionRepository, String userId, String tenantId)
        """
        try:
            userSession = UserSessions()
            loginTime = datetime.now()
            
            userSession.tenant = tenantId
            
            user_ref = UserRef()
            user_ref.id = userId
            
            userSession.loginDatetime = loginTime
            userSession.user = user_ref
            
            saved_session = await self.userSessionRepository.save(userSession)
            return saved_session.id
            
        except Exception as e:
            self.LOG.error(f"Error setting user session: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating user session"
            )

    async def setUserSessionLogoutTime(self, userSessionObjectID: str) -> None:
        """
        Set logout time for user session
        Equivalent to Java: setUserSessionLogoutime(String userSessionObjectID)
        """
        try:
            userSession = await self.userSessionRepository.findById(userSessionObjectID)
            if userSession:
                logoutTime = datetime.now()
                userSession.logoutDatetime = logoutTime
                await self.userSessionRepository.save(userSession)
                
        except Exception as e:
            self.LOG.error(f"Error setting logout time: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating session logout time"
            )

    async def isAccountLocked(self, userId: str) -> bool:
        """
        Check if account is locked due to failed login attempts
        Equivalent to Java: isAccountLocked(String userId)
        """
        try:
            user = await self.userRepository.findById(userId)
            if not user:
                return False
                
            attempts = user.loginAttempts or 0
            lockoutTime = user.lockoutTime or 0
            currentTime = int(datetime.now().timestamp() * 1000)
            
            # If attempts exceeded but lockout time has passed, reset and unlock
            if attempts >= self.MAX_ATTEMPTS + 1 and lockoutTime < currentTime:
                await self.resetLoginAttempts(userId)
                return False
            
            # If still within lockout period
            if lockoutTime > currentTime:
                return True
                
            return False
            
        except Exception as e:
            self.LOG.error(f"Error checking account lock status: {str(e)}")
            return False

    async def resetLoginAttempts(self, userId: str) -> None:
        """
        Reset login attempts and unlock account
        Equivalent to Java: resetLoginAttempts(String userId)
        """
        try:
            user = await self.userRepository.findById(userId)
            if user:
                user.loginAttempts = 0
                user.lockoutTime = 0
                await self.userRepository.save(user)
                
        except Exception as e:
            self.LOG.error(f"Error resetting login attempts: {str(e)}")

    async def getRemainingLockoutTime(self, userId: str) -> int:
        """
        Get remaining lockout time in milliseconds
        Equivalent to Java: getRemainingLockoutTime(String userId)
        """
        try:
            user = await self.userRepository.findById(userId)
            if user and user.lockoutTime:
                currentTime = int(datetime.now().timestamp() * 1000)
                return max(0, user.lockoutTime - currentTime)
            return 0
            
        except Exception as e:
            self.LOG.error(f"Error getting remaining lockout time: {str(e)}")
            return 0

    async def incrementLoginAttempts(self, userId: str) -> None:
        """
        Increment login attempts and lock account if max attempts reached
        Equivalent to Java: incrementLoginAttempts(String userId)
        """
        try:
            user = await self.userRepository.findById(userId)
            if not user:
                return
                
            attempts = (user.loginAttempts or 0) + 1
            user.loginAttempts = attempts
            await self.userRepository.save(user)
            
            if attempts >= self.MAX_ATTEMPTS:
                currentTime = int(datetime.now().timestamp() * 1000)
                user.lockoutTime = currentTime + self.LOCKOUT_TIME
                user.loginAttempts = self.MAX_ATTEMPTS + 1
                await self.userRepository.save(user)
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account Locked"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            self.LOG.error(f"Error incrementing login attempts: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing login attempt"
            )

    async def validateToken(self, credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """
        Validate JWT token and return user info
        Additional method for FastAPI authentication
        """
        try:
            token = credentials.credentials
            payload = await self.jwtUtil.validateToken(token)
            return payload
            
        except Exception as e:
            self.LOG.error(f"Token validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"}
            )

    async def getCurrentUser(self, credentials: HTTPAuthorizationCredentials) -> User:
        """
        Get current authenticated user from token
        Additional method for FastAPI dependency injection
        """
        try:
            payload = await self.validateToken(credentials)
            userId = payload.get("userId")
            
            if not userId:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
                
            user = await self.userRepository.findById(userId)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
                
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            self.LOG.error(f"Error getting current user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving user information"
            )
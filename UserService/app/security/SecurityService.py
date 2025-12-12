# This file replaces JwtUserDetailService.java
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.models.aggregates.root.User import User
from app.models.valueobjects import Email, Tenant
from app.repositories.UserRepository import UserRepository
from app.repositories.UserSessionRepository import UserSessionRepository
from app.models.entity.UserSessions import UserSessions
from .JwtUtil import JwtUtil

class SecurityService:
    MAX_ATTEMPTS = 3
    LOCKOUT_TIME_MINUTES = 1

    def __init__(
        self,
        userRepository: UserRepository,
        userSessionRepository: UserSessionRepository,
        jwtUtil: JwtUtil
    ):
        self.userRepository = userRepository
        self.userSessionRepository = userSessionRepository
        self.jwtUtil = jwtUtil
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async def authenticate(self, username: str, password: str, tenantId: str) -> User:
        user = await self.userRepository.findByEmailAndTenant(Email(officialEmail=username), Tenant(tenantId=tenantId))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad credentials")

        # Plain-text verification per current storage policy
        if password != (user.password.password if user.password else ""):
            await self.incrementLoginAttempts(user.id)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad credentials")

        if await self.isAccountLocked(user.id):
            remaining_time = await self.getRemainingLockoutTime(user.id)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account is locked. Wait for {remaining_time.total_seconds()} seconds."
            )

        await self.resetLoginAttempts(user.id)
        return user

    async def createJwtToken(self, user: User, tenantId: str) -> Dict[str, str]:
        user_session_id = await self.setUserSession(user.id, tenantId)
        access_token = self.jwtUtil.generate(user, "ACCESS", tenantId, user_session_id)
        refresh_token = self.jwtUtil.generate(user, "REFRESH", tenantId, user_session_id)
        return {"accessToken": access_token, "refreshToken": refresh_token}

    async def setUserSession(self, userId: str, tenantId: str) -> str:
        user_ref = {"id": userId} # Simplified reference
        user_session = UserSessions(
            tenant=tenantId,
            user=user_ref,
            loginDatetime=datetime.now(timezone.utc)
        )
        saved_session = await self.userSessionRepository.save(user_session)
        return str(saved_session.id)

    async def setUserSessionLogoutTime(self, userSessionObjectId: str):
        session = await self.userSessionRepository.findById(userSessionObjectId)
        if session:
            session.logoutDatetime = datetime.now(timezone.utc)
            await self.userSessionRepository.save(session)

    async def isAccountLocked(self, userId: str) -> bool:
        user = await self.userRepository.findById(userId)
        if not user: return True
        
        lockout_time_utc = user.lockoutTime.replace(tzinfo=timezone.utc) if user.lockoutTime else None
        
        if user.loginAttempts >= self.MAX_ATTEMPTS + 1 and lockout_time_utc and lockout_time_utc > datetime.now(timezone.utc):
            return True
        elif user.loginAttempts >= self.MAX_ATTEMPTS + 1 and (not lockout_time_utc or lockout_time_utc <= datetime.now(timezone.utc)):
            await self.resetLoginAttempts(userId)
            return False
            
        return False

    async def resetLoginAttempts(self, userId: str):
        user = await self.userRepository.findById(userId)
        if user:
            user.loginAttempts = 0
            user.lockoutTime = None
            await self.userRepository.save(user)

    async def getRemainingLockoutTime(self, userId: str) -> timedelta:
        user = await self.userRepository.findById(userId)
        if not user or not user.lockoutTime:
            return timedelta(0)
        
        lockout_time_utc = user.lockoutTime.replace(tzinfo=timezone.utc)
        remaining = lockout_time_utc - datetime.now(timezone.utc)
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    async def incrementLoginAttempts(self, userId: str):
        user = await self.userRepository.findById(userId)
        if user:
            user.loginAttempts += 1
            if user.loginAttempts >= self.MAX_ATTEMPTS:
                user.lockoutTime = datetime.now(timezone.utc) + timedelta(minutes=self.LOCKOUT_TIME_MINUTES)
            await self.userRepository.save(user)
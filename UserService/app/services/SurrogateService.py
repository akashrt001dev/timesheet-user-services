import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status

# Using EmailMessageSupplier for messaging
from app.pubsub.EmailMessageSupplier import EmailMessageSupplier
from app.core.constants import AppConstants
from app.models.DTO.SurrogateLogDTO import SurrogateLogDTO
from app.core.QueryProcessor import QueryProcessor
from app.models.aggregates.root.User import User
from app.models.entity.SurrogateLog import SurrogateLog
from app.models.valueobjects.SurrogateSchedule import SurrogateSchedule
from app.models.valueobjects.SurrogateUser import SurrogateUser
from app.models.valueobjects.Tenant import Tenant
from app.repositories.SurrogateLogRepository import SurrogateLogRepository
from app.repositories.UserRepository import UserRepository
from app.scheduler.UserJobScheduler import UserJobScheduler

class SurrogateService:
    def __init__(
        self,
        surrogateLogRepository: SurrogateLogRepository,
        userRepository: UserRepository,
        queryProcessor: QueryProcessor,
        emailMessageSupplier: EmailMessageSupplier, # Replaces StreamBridge
        userJobScheduler: UserJobScheduler # Replaces JobService
    ):
        self.surrogateLogRepository = surrogateLogRepository
        self.userRepository = userRepository
        self.queryProcessor = queryProcessor
        self.emailMessageSupplier = emailMessageSupplier
        self.userJobScheduler = userJobScheduler
        self.LOG = logging.getLogger(__name__)

    async def assignSurrogate(self, tenantId: str, surrogateDTO: SurrogateLogDTO, id: Optional[str], isUpdate: bool) -> SurrogateLog:
        surrogate = surrogateDTO.to_domain()
        surrogate.tenant = Tenant(id=tenantId)
        
        if isUpdate and id:
            surrogate.id = id
        
        await self.surrogateLogRepository.save(surrogate)
        await self._updateSurrogateUserSchedule(surrogate, isUpdate)
        return surrogate

    async def _updateSurrogateUserSchedule(self, surrogateLog: SurrogateLog, isUpdate: bool):
        user = await self.userRepository.findById(surrogateLog.surrogate.id)
        if not user:
            await self.surrogateLogRepository.delete(surrogateLog.id)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid surrogateUser ID")

        surrogateSchedule = SurrogateSchedule(
            surrogateLogId=surrogateLog.id,
            surrogateFor=surrogateLog.user,
            startDate=surrogateLog.startDate,
            endDate=surrogateLog.endDate
        )

        if isUpdate:
            await self._removeSurrogateScheduleAndDeleteJob(user, surrogateLog)

        if user.surrogateSchedule is None:
            user.surrogateSchedule = []
        
        user.surrogateSchedule.append(surrogateSchedule)
        
        await self.userJobScheduler.schedule_surrogate_removal_job(surrogateSchedule, user, surrogateLog.id)
        
        await self.userRepository.save(user)
        await self.surrogateLogRepository.save(surrogateLog)
        
        await self._updateUserTimesheetSettings(user)

    async def getAllTimeHoldersForIssuer(self, tenantId: str, issuerId: str) -> List[SurrogateLog]:
        return await self.surrogateLogRepository.getAllTimeHoldersForIssuer(tenantId, issuerId)

    async def getCurrentHoldersForIssuer(self, tenantId: str, issuerId: str) -> List[SurrogateLog]:
        return await self.queryProcessor.getCurrentHoldersForIssuer(tenantId, issuerId)

    async def getIssuersForHolder(self, tenantId: str, holderId: str) -> List[SurrogateUser]:
        user = await self.userRepository.findById(holderId)
        if not user or not user.surrogateSchedule:
            return []

        # Convert to local timezone for proper day boundary comparison like Java
        from datetime import date, time
        current_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=999999)
        
        active_issuers = [
            schedule.surrogateFor for schedule in user.surrogateSchedule
            if (schedule.startDate <= current_date or schedule.startDate == current_date) and 
               (schedule.endDate >= end_of_day or schedule.endDate == end_of_day)
        ]
        
        # Return distinct issuers by their ID
        return list({issuer.id: issuer for issuer in active_issuers}.values())

    async def unassignSurrogate(self, tenantId: str, id: str):
        surrogateLog = await self.surrogateLogRepository.findById(id)
        if not surrogateLog:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Surrogate log not found")

        user = await self.userRepository.findById(surrogateLog.surrogate.id)
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Surrogate user not found")

        now = datetime.now(timezone.utc)
        if now < surrogateLog.startDate:
            await self._removeSurrogateScheduleAndDeleteJob(user, surrogateLog)
            await self.surrogateLogRepository.deleteById(id)
        else:
            user.surrogateSchedule = [s for s in user.surrogateSchedule if s.surrogateLogId != id]
            await self.userJobScheduler.delete_surrogate_job(surrogateLog)
            surrogateLog.endDate = now
            await self.surrogateLogRepository.save(surrogateLog)
        
        await self.userRepository.save(user)
        await self._updateUserTimesheetSettings(user)
        # In FastAPI, returning a status is handled by the route handler.
        # A successful execution implies acceptance. A 202 status code is appropriate.

    async def _removeSurrogateScheduleAndDeleteJob(self, user: User, surrogateLog: SurrogateLog):
        if not user.surrogateSchedule:
            return
            
        original_len = len(user.surrogateSchedule)
        user.surrogateSchedule = [s for s in user.surrogateSchedule if s.surrogateLogId != surrogateLog.id]

        if len(user.surrogateSchedule) < original_len:
            await self.userJobScheduler.delete_surrogate_job(surrogateLog)

    async def _updateUserTimesheetSettings(self, user: User):
        # In Python, this would publish the user object to a specific RabbitMQ queue/topic
        await self.emailMessageSupplier.send_user_update(AppConstants.USER_PRODUCER_BINDING_NAME, user.dict())
    
    # ===== METHODS CALLED BY SURROGATE CONTROLLER =====
    
    async def unassignSurrogate(self, tenantId: str, surrogateId: str) -> None:
        """
        Unassign surrogate by removing the surrogate relationship
        Java: unAssignSurrogate
        """
        try:
            surrogateLog = await self.surrogateLogRepository.findById(surrogateId)
            if not surrogateLog:
                raise HTTPException(status_code=404, detail="Surrogate assignment not found")
            
            # Remove from user's surrogate schedule
            user = await self.userRepository.findById(surrogateLog.surrogate.id)
            if user:
                await self._removeSurrogateScheduleAndDeleteJob(user, surrogateLog)
                await self.userRepository.save(user)
                await self._updateUserTimesheetSettings(user)
            
            # Delete the surrogate log
            await self.surrogateLogRepository.delete(surrogateId)
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=400, detail=f"Failed to unassign surrogate: {str(e)}")
    
    async def getAllTimeHoldersForIssuer(self, tenantId: str, issuerId: str) -> List[SurrogateLog]:
        """
        Get all time holders for a specific issuer
        Java: getAllTimeHolders
        """
        try:
            return await self.surrogateLogRepository.findByIssuerIdAndTenantId(issuerId, tenantId)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to get time holders: {str(e)}")
    
    async def getCurrentHoldersForIssuer(self, tenantId: str, issuerId: str) -> List[SurrogateLog]:
        """
        Get current active time holders for a specific issuer
        Java: getCurrentHolders
        """
        try:
            current_date = datetime.now(timezone.utc)
            all_holders = await self.getAllTimeHoldersForIssuer(tenantId, issuerId)
            
            # Filter for currently active assignments
            current_holders = []
            for holder in all_holders:
                if (holder.surrogateSchedule and 
                    holder.surrogateSchedule.startDate <= current_date <= holder.surrogateSchedule.endDate):
                    current_holders.append(holder)
            
            return current_holders
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to get current holders: {str(e)}")
    
    async def getIssuersForHolder(self, tenantId: str, holderId: str) -> List[SurrogateUser]:
        """
        Get all issuers for whom this user is a surrogate holder
        Java: getIssuersForHolder
        """
        try:
            surrogate_logs = await self.surrogateLogRepository.findByHolderIdAndTenantId(holderId, tenantId)
            
            issuers = []
            for log in surrogate_logs:
                if log.issuer:
                    issuers.append(log.issuer)
            
            return issuers
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to get issuers for holder: {str(e)}")
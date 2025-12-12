from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, TYPE_CHECKING, Type
from .MongoRepository import MongoRepository

if TYPE_CHECKING:
    from ..models.entity.SurrogateLog import SurrogateLog

class SurrogateLogRepository(MongoRepository['SurrogateLog']):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "surrogate_logs")

    def get_model_class(self) -> Type['SurrogateLog']:
        from ..models.entity.SurrogateLog import SurrogateLog
        return SurrogateLog

    async def getAllTimeHoldersForIssuer(self, tenantId: str, issuerId: str) -> List['SurrogateLog']:
        """
        Finds all surrogate logs for a given issuer within a tenant.
        Java Query: {'tenant._id' : ?0, 'user._id' : ?1 }
        """
        query = {"tenant._id": tenantId, "user._id": issuerId}
        return await self.find_by_filter(query)
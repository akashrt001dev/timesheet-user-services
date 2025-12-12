from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional, TYPE_CHECKING, Type
from .MongoRepository import MongoRepository

if TYPE_CHECKING:
    from ..models.entity.UserActivationLinkId import UserActivationLinkId

class UserActivationLinkIdRepository(MongoRepository['UserActivationLinkId']):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "user_activation_links")

    def get_model_class(self) -> Type['UserActivationLinkId']:
        from ..models.entity.UserActivationLinkId import UserActivationLinkId
        return UserActivationLinkId

    async def findByUserId(self, userId: str) -> Optional['UserActivationLinkId']:
        return await self.find_one_by_filter({"userId": userId})

    async def getUserByTenantIDandHashCode(self, tenantId: str, hashcode: str) -> Optional['UserActivationLinkId']:
        """Java Query: {'tenantId':?0, 'hashcode' :?1 }"""
        return await self.find_one_by_filter({"tenantId": tenantId, "hashcode": hashcode})

    async def getAllIdsByUser(self, userId: str) -> List['UserActivationLinkId']:
        """Java Query: {'userId':?0}"""
        return await self.find_by_filter({"userId": userId})

    async def findByHashcode(self, hashcode: str) -> Optional['UserActivationLinkId']:
        """Java Query: {'hashcode' :?0 }"""
        return await self.find_one_by_filter({"hashcode": hashcode})

    async def findByHashedUuid(self, hashedUuid: str) -> Optional['UserActivationLinkId']:
        """
        Compatibility finder: try both 'hashedUuid' (our Python) and 'hashcode' (legacy Java) fields.
        """
        # Try Python field name first
        doc = await self.find_one_by_filter({"hashedUuid": hashedUuid})
        if doc:
            return doc
        # Fallback to Java field name
        return await self.find_one_by_filter({"hashcode": hashedUuid})
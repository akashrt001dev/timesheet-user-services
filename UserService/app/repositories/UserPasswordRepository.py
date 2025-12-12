from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, TYPE_CHECKING, Type
from .MongoRepository import MongoRepository

if TYPE_CHECKING:
    from ..models.entity.UserPassword import UserPassword

class UserPasswordRepository(MongoRepository['UserPassword']):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "user_passwords")

    def get_model_class(self) -> Type['UserPassword']:
        from ..models.entity.UserPassword import UserPassword
        return UserPassword

    async def findByUserId(self, userId: str) -> Optional['UserPassword']:
        return await self.find_one_by_filter({"userId": userId})
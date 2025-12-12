from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import TYPE_CHECKING, Type
from .MongoRepository import MongoRepository

if TYPE_CHECKING:
    from ..models.entity.UserSessions import UserSessions

class UserSessionRepository(MongoRepository['UserSessions']):
    def __init__(self, db: AsyncIOMotorDatabase):
        # Align with QueryProcessor expectations: collection name 'user_session'
        super().__init__(db, "user_session")

    def get_model_class(self) -> Type['UserSessions']:
        from ..models.entity.UserSessions import UserSessions
        return UserSessions

    # The original Java interface had no custom methods.
    # All standard CRUD operations are inherited from MongoRepository.
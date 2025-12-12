from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, TYPE_CHECKING, Type
from .MongoRepository import MongoRepository

if TYPE_CHECKING:
    from ..models.entity.ProfilePicture import ProfilePicture
    from ..models.valueobjects.UserId import UserId

class ProfilePictureRepository(MongoRepository['ProfilePicture']):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "profile_pictures")

    def get_model_class(self) -> Type['ProfilePicture']:
        from ..models.entity.ProfilePicture import ProfilePicture
        return ProfilePicture

    async def findByUserId(self, userId: 'UserId') -> Optional['ProfilePicture']:
        """Finds a profile picture by user ID."""
        user_id_dict = userId.dict() if hasattr(userId, 'dict') else userId.model_dump()
        return await self.find_one_by_filter({"userId": user_id_dict})
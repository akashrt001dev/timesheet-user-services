from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, TYPE_CHECKING, Type
from .MongoRepository import MongoRepository

if TYPE_CHECKING:
    from ..models.valueobjects.UserJobDetails import UserJobDetails

class UserJobDetailsRepository(MongoRepository['UserJobDetails']):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "user_job_details")

    def get_model_class(self) -> Type['UserJobDetails']:
        from ..models.valueobjects.UserJobDetails import UserJobDetails
        return UserJobDetails

    async def getUserJobDetailsBySurrogateLogId(self, surrogateLogId: str) -> Optional['UserJobDetails']:
        """
        Java Query: {'surrogateJobDetails.surrogateLogId' : ?0}
        """
        return await self.find_one_by_filter({"surrogateJobDetails.surrogateLogId": surrogateLogId})
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, TYPE_CHECKING, Type
from .MongoRepository import MongoRepository

if TYPE_CHECKING:
    from ..models.entity.Role import Role

class RoleRepository(MongoRepository['Role']):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "role")

    def get_model_class(self) -> Type['Role']:
        from ..models.entity.Role import Role
        return Role

    async def findByRoleTypes(self, roleTypes: List[str]) -> List['Role']:
        """Finds roles by a list of role types.
        Java Query: {'roleType': {'$in' :?0} }
        """
        return await self.find_by_filter({"roleType": {"$in": roleTypes}})

    async def findByRoleNames(self, roleNames: List[str]) -> List['Role']:
        """Finds roles by a list of role names.
        Java Query: {'roleName': {'$in' :?0}}
        """
        return await self.find_by_filter({"roleName": {"$in": roleNames}})
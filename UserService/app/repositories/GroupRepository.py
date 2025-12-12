from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, TYPE_CHECKING, Type
from .MongoRepository import MongoRepository

if TYPE_CHECKING:
    from ..models.entity.Group import Group
    from ..models.valueobjects.Tenant import Tenant

class GroupRepository(MongoRepository['Group']):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "groups")

    def get_model_class(self) -> Type['Group']:
        from ..models.entity.Group import Group
        return Group

    async def findByTenant(self, tenant: 'Tenant') -> List['Group']:
        """Finds all groups for a given tenant."""
        tenant_dict = tenant.dict() if hasattr(tenant, 'dict') else tenant.model_dump()
        return await self.find_by_filter({"tenant": tenant_dict})
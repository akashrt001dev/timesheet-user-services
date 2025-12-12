from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional, TYPE_CHECKING, Type, Any
from .MongoRepository import MongoRepository
from bson import ObjectId

if TYPE_CHECKING:
    from ..models.aggregates.root.User import User
    from ..models.valueobjects.Email import Email
    from ..models.valueobjects.SsoId import SsoId
    from ..models.valueobjects.Tenant import Tenant

class UserRepository(MongoRepository['User']):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "user")  # Use the correct collection name

    def get_model_class(self) -> Type['User']:
        from ..models.aggregates.root.User import User
        return User

    async def findByEmail(self, email: Any) -> Optional['User']:
        """Find by Email value object or raw email string."""
        if isinstance(email, str):
            # Stored shape: { email: { officialEmail: <str> } }
            return await self.find_one_by_filter({"email.officialEmail": email})
        # Pydantic v2 first, then v1
        if hasattr(email, 'model_dump'):
            email_dict = email.model_dump()
        elif hasattr(email, 'dict'):
            email_dict = email.dict()
        else:
            # Best effort: treat as dict-like or build from attribute
            try:
                email_dict = {"officialEmail": getattr(email, 'officialEmail')}
            except Exception:
                email_dict = {"officialEmail": str(email)}
        return await self.find_one_by_filter({"email": email_dict})

    async def findByTenant(self, tenant: 'Tenant') -> List['User']:
        # Query by tenant.tenantId field to match the MongoDB document structure
        query = {"tenant.tenantId": tenant.tenantId}
        print(f"UserRepository.findByTenant query: {query}")
        return await self.find_by_filter(query)

    async def findByEmailAndTenant(self, email: Any, tenant: 'Tenant') -> Optional['User']:
        """Find by Email (value object or string) and Tenant (object or id string)."""
        # Normalize email
        if isinstance(email, str):
            email_filter = {"email.officialEmail": email}
        else:
            if hasattr(email, 'model_dump'):
                email_dict = email.model_dump()
            elif hasattr(email, 'dict'):
                email_dict = email.dict()
            else:
                try:
                    email_dict = {"officialEmail": getattr(email, 'officialEmail')}
                except Exception:
                    email_dict = {"officialEmail": str(email)}
            email_filter = {"email": email_dict}

        # Normalize tenant id
        tenant_id = getattr(tenant, 'tenantId', tenant)
        return await self.find_one_by_filter({**email_filter, "tenant.tenantId": tenant_id})

    async def findByIdAndTenant(self, id: str, tenant: 'Tenant') -> Optional['User']:
        """Find a user by id and tenant, tolerating different storage shapes.
        Supports both ObjectId and string _id, and tenant stored as:
        - tenant.tenantId
        - tenant (string)
        - tenant { tenantId }
        - tenant._id
        - root-level tenantId
        """
        tenant_id = tenant.tenantId
        # Build robust _id filter that matches ObjectId and string forms
        id_filter = self._id_query(id)
        # Possible tenant shapes
        tenant_filters = [
            {"tenant.tenantId": tenant_id},
            {"tenant": tenant_id},
            {"tenant": {"tenantId": tenant_id}},
            {"tenant._id": tenant_id},
            {"tenantId": tenant_id},
        ]
        # If tenant id looks like an ObjectId, try that for tenant._id as well
        if isinstance(tenant_id, str) and ObjectId.is_valid(tenant_id):
            tenant_filters.append({"tenant._id": ObjectId(tenant_id)})

        # Try combinations until one hits
        for tf in tenant_filters:
            query = {**id_filter, **tf}
            doc = await self.find_one_by_filter(query)
            if doc:
                return doc
        return None

    async def getUsersByTenantIDandRole(self, tenant: 'Tenant', roleName: List[str], sort: Optional[list] = None) -> List['User']:
        """Java Query: {'tenant':?0, 'roles.roleName' : {$in:?1} }"""
        # Query by tenant.tenantId field to match the MongoDB document structure
        query = {"tenant.tenantId": tenant.tenantId, "roles.roleName": {"$in": roleName}}
        return await self.find_by_filter(query, sort=sort)

    async def getUnInvitedUsersByTenantIDandContract(self, contractId: str) -> List['User']:
        """Java Query: {'contracts' : {$elemMatch:{'_id':?0}},'isInvited':false }"""
        query = {"contracts": {"$elemMatch": {"_id": contractId}}, "isInvited": False}
        return await self.find_by_filter(query)

    async def findBySsoIdAndTenant(self, ssoId: str, tenant: 'Tenant') -> Optional['User']:
        """Java Query: {'ssoId._id': { $regex: ?0, $options: 'i' }, 'tenant': ?1}"""
        # Query by tenant.tenantId field to match the MongoDB document structure
        query = {"ssoId._id": {"$regex": ssoId, "$options": "i"}, "tenant.tenantId": tenant.tenantId}
        return await self.find_one_by_filter(query)

    async def findBySsoId(self, ssoId: Any) -> Optional['User']:
        """Find by SsoId value object or raw string."""
        if isinstance(ssoId, str):
            return await self.find_one_by_filter({"ssoId._id": {"$regex": ssoId, "$options": "i"}})
        if hasattr(ssoId, 'model_dump'):
            sso_id_dict = ssoId.model_dump()
        elif hasattr(ssoId, 'dict'):
            sso_id_dict = ssoId.dict()
        else:
            sso_id_dict = {"_id": getattr(ssoId, 'id', str(ssoId))}
        return await self.find_one_by_filter({"ssoId": sso_id_dict})

    async def findBySsoIdAndTenant(self, ssoId: Any, tenant: 'Tenant') -> Optional['User']:
        """Find by SsoId (value object or string) and tenant.
        Be tolerant of different tenant storage shapes (tenant.tenantId, tenant as string, nested dict, or root tenantId/_id).
        """
        tenant_id = getattr(tenant, 'tenantId', tenant)

        # Build SSO filter variants
        if isinstance(ssoId, str):
            sso_filters = [{"ssoId._id": {"$regex": ssoId, "$options": "i"}}]
        else:
            if hasattr(ssoId, 'model_dump'):
                sso_id_dict = ssoId.model_dump()
            elif hasattr(ssoId, 'dict'):
                sso_id_dict = ssoId.dict()
            else:
                sso_id_dict = {"_id": getattr(ssoId, 'id', str(ssoId))}
            # Try both nested object and direct _id match
            sso_filters = [
                {"ssoId": sso_id_dict},
                {"ssoId._id": {"$regex": sso_id_dict.get("_id", ""), "$options": "i"}},
            ]

        # Possible tenant shapes seen in legacy data
        tenant_filters = [
            {"tenant.tenantId": tenant_id},              # Preferred nested field
            {"tenant": tenant_id},                       # Direct string tenant
            {"tenant": {"tenantId": tenant_id}},       # Nested dict tenant
            {"tenant._id": tenant_id},                   # Nested _id variant
            {"tenantId": tenant_id},                     # Root-level tenantId
        ]

        # Try combinations until one hits
        for sf in sso_filters:
            for tf in tenant_filters:
                doc = await self.find_one_by_filter({**sf, **tf})
                if doc:
                    return doc
        return None

    async def findAllByIdIn(self, userIds: List[str]) -> List['User']:
        return await self.find_by_ids(userIds)

    async def getUnInvitedAggregatorUserByTenantIDandContract(self, contractId: str, roleName: str) -> List['User']:
        """Java Query: {'contracts' : {$elemMatch:{'_id':?0}},'isInvited':false,'roles' : {$elemMatch:{'roleName':?1}} }"""
        query = {
            "contracts": {"$elemMatch": {"_id": contractId}},
            "isInvited": False,
            "roles": {"$elemMatch": {"roleName": roleName}}
        }
        return await self.find_by_filter(query)

    async def getUsersByContractId(self, contractId: str) -> List['User']:
        """Java Query: {'contracts' : {$elemMatch:{'_id':?0}} }"""
        query = {"contracts": {"$elemMatch": {"_id": contractId}}}
        return await self.find_by_filter(query)

    async def getUsersByExternalIds(self, userExternalIds: List[str]) -> List['User']:
        """Java Query: {'externalId': { $in: ?0 }}"""
        return await self.find_by_filter({"externalId": {"$in": userExternalIds}})

    async def findByExternalId(self, externalId: str) -> Optional['User']:
        return await self.find_one_by_filter({"externalId": externalId})

    async def findBySsoIdIgnoreCase(self, ssoId: str) -> Optional['User']:
        """Java Query: {'ssoId._id': { $regex: ?0, $options: 'i' }}"""
        query = {"ssoId._id": {"$regex": ssoId, "$options": "i"}}
        return await self.find_one_by_filter(query)

    async def getUsersByUserIdAndContractId(self, Id: str, contractId: str) -> Optional['User']:
        """Java Query: {'_id' : ?0, 'contracts' : {$elemMatch:{'_id':?1}} }"""
        _id = ObjectId(Id) if ObjectId.is_valid(Id) else Id
        query = {"_id": _id, "contracts": {"$elemMatch": {"_id": contractId}}}
        return await self.find_one_by_filter(query)

    async def getUsersByTitleAndSiteId(self, title: List[str], siteId: str) -> List['User']:
        """Java Query: {'sites.sites.siteResponsibility._id': { $in: ?0 }, 'sites.sites._id' : ?1}"""
        query = {"sites.sites.siteResponsibility._id": {"$in": title}, "sites.sites._id": siteId}
        return await self.find_by_filter(query)
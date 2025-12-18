from datetime import datetime, timedelta, timezone, date
from typing import List, Dict, Any, Optional, Set
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from motor.motor_asyncio import AsyncIOMotorDatabase

# Assuming these imports point to your actual Pydantic models and other components
from app.core.constants import AppConstants
from app.models.DTO.UserListDTO import UserListDTO
from app.models.aggregates.root.User import User
from app.models.entity.Role import Role
from app.models.entity.SurrogateLog import SurrogateLog
from app.models.valueobjects.Email import Email
from app.models.valueobjects.Tenant import Tenant
from app.models.valueobjects.UserRoles import UserRoles
from app.models.valueobjects.UserType import UserType
from app.repositories.UserRepository import UserRepository

class QueryProcessor:
    """
    Handles complex, dynamic queries and aggregations against the MongoDB database.
    Migrated from QueryProcessor.java, using Motor instead of MongoTemplate.
    """
    def __init__(self, db: AsyncIOMotorDatabase, userRepository: UserRepository):
        self.db = db
        self.user_collection = db.get_collection("user")  # Use the correct collection name
        self.user_session_collection = db.get_collection("user_session")
        self.surrogate_log_collection = db.get_collection("surrogate_logs")
        self.userRepository = userRepository
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"QueryProcessor initialized with collection: {self.user_collection.name}")
        self.n_days_before = 30

    async def getUsersByEmailIdList(self, emailList: List[Email]) -> List[User]:
        email_strs = [email.officialEmail for email in emailList]
        query = {"email.officialEmail": {"$in": email_strs}}
        cursor = self.user_collection.find(query)
        return [User(**doc) async for doc in cursor]

    def userNameQuery(self, firstName: Optional[str], lastName: Optional[str], query: Dict[str, Any]):
        """Helper to build username regex queries."""
        if firstName:
            query["name.firstName"] = {"$regex": firstName, "$options": "i"}
        if lastName:
            query["name.lastName"] = {"$regex": lastName, "$options": "i"}

    async def getFilteredUsers(
        self, tenant: Tenant, firstName: Optional[str], lastName: Optional[str], 
        contractId: Optional[str], activated: Optional[str], userType: Optional[str], 
        blocked: Optional[str], invited: Optional[str], partnerId: Optional[str], 
        sites: Optional[List[str]], titles: Optional[List[str]], 
        sitedepartments: Optional[List[str]], contractIdOnFile: Optional[str], 
        userTypes: Optional[List[str]], searchText: Optional[str], 
        offset: int, limit: int
    ) -> UserListDTO:
        
        import logging
        logger = logging.getLogger(__name__)
        
        query: Dict[str, Any] = {"tenant.tenantId": tenant.tenantId}
        logger.info(f"QueryProcessor: Building query for tenant: {tenant.tenantId}")
        logger.info(f"QueryProcessor: Using collection: {self.user_collection.name}")

        # Early return for contractId filter
        if contractId:
            query["contracts._id"] = contractId
            dummy_user = await self.userRepository.getUsersByUserIdAndContractId(
                AppConstants.DUMMY_USER_ID, contractId
            )
            if dummy_user:
                return UserListDTO(users=[dummy_user], numberOfElements=1)

        # Build basic filters
        self.userNameQuery(firstName, lastName, query)

        if activated is not None:
            query["isActivated"] = (activated.lower() == 'true')
        
        # User type filters
        all_user_types = []
        if userType:
            all_user_types.append(userType)
        if userTypes:
            all_user_types.extend(userTypes)
        if all_user_types:
            query["userType"] = {"$in": all_user_types}

        if blocked is not None:
            query["isBlocked"] = (blocked.lower() == 'true')
        
        if invited is not None:
            query["isDeleted"] = False
            query["isInvited"] = (invited.lower() == 'true')

        if partnerId:
            query["partnerId._id"] = partnerId

        if contractIdOnFile:
            query["contracts.contractID.contractID"] = contractIdOnFile

        # Handle titles
        if titles:
            query["sites.sites.siteResponsibility._id"] = {"$in": titles}
            query["sites.sites.siteResponsibility"] = {"$exists": True}

        # Handle complex site and department filtering with $elemMatch
        site_or_clauses = []
        if sites:
            site_or_clauses.append({"sites.sites": {"$elemMatch": {"_id": {"$in": sites}}}})
        
        if sitedepartments:
            dept_or_clauses = []
            for item in sitedepartments:
                site_id, dept_id = item.split("#")
                dept_or_clauses.append({
                    "sites.sites": {
                        "$elemMatch": {
                            "_id": site_id,
                            "departmentList.departments": {"$elemMatch": {"_id": dept_id}}
                        }
                    }
                })
            if dept_or_clauses:
                site_or_clauses.append({"$or": dept_or_clauses})

        if site_or_clauses:
            query["$or"] = query.get("$or", []) + site_or_clauses

        # Handle text search
        if searchText:
            search_regex = {"$regex": searchText, "$options": "i"}
            query["$or"] = query.get("$or", []) + [
                {"name.firstName": search_regex},
                {"name.lastName": search_regex},
                {"ssoId._id": search_regex},
            ]

        logger.info(f"QueryProcessor: Final query: {query}")
        total_count = await self.user_collection.count_documents(query)
        logger.info(f"QueryProcessor: Query returned {total_count} documents")
        
        # Handle pagination
        if offset <= 0 and limit <= 0:
            # No pagination - return all results
            cursor = self.user_collection.find(query)
            all_users = []
            async for doc in cursor:
                try:
                    # Convert MongoDB _id to string id
                    if "_id" in doc:
                        doc["id"] = str(doc["_id"])
                        del doc["_id"]
                    user = User(**doc)
                    all_users.append(user)
                except Exception as e:
                    logger.error(f"Error creating User from doc: {e}")
                    continue
            return UserListDTO(users=all_users, numberOfElements=total_count)
        else:
            # With pagination
            start_index = min(offset * limit, total_count)
            paginated_cursor = self.user_collection.find(query).skip(start_index).limit(limit)
            paginated_list = []
            async for doc in paginated_cursor:
                try:
                    # Convert MongoDB _id to string id
                    if "_id" in doc:
                        doc["id"] = str(doc["_id"])
                        del doc["_id"]
                    user = User(**doc)
                    paginated_list.append(user)
                except Exception as e:
                    logger.error(f"Error creating User from doc: {e}")
                    continue
            return UserListDTO(users=paginated_list, numberOfElements=total_count)

    def _getBaseMetaDataQuery(self, tenantId: str, siteId: Optional[str]) -> Dict[str, Any]:
        query = {
            "isDeleted": False,
            "tenant.tenantId": tenantId
        }
        if siteId:
            query["sites.sites"] = {"$elemMatch": {"_id": siteId}}
        return query

    async def getRegisteredUsersMetadata(self, tenantId: str, siteId: Optional[str]) -> Dict[str, int]:
        query = self._getBaseMetaDataQuery(tenantId, siteId)
        all_registered_users_count = await self.user_collection.count_documents(query)
        
        blocked_query = query.copy()
        blocked_query["isBlocked"] = True
        all_blocked_users = await self.user_collection.count_documents(blocked_query)

        return {
            "allRegisteredUsersCount": all_registered_users_count,
            "allBlockedUsers": all_blocked_users
        }

    async def getUserAvgLoginCount(self, userID: str) -> int:
        start_date = datetime.utcnow() - timedelta(days=self.n_days_before)
        
        pipeline = [
            {"$match": {"user._id": ObjectId(userID), "loginDatetime": {"$gte": start_date}}},
            {"$project": {
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$loginDatetime", "timezone": "UTC"}}
            }},
            {"$group": {"_id": "$date", "count": {"$sum": 1}}},
            {"$group": {"_id": None, "avgLogin": {"$avg": "$count"}}}
        ]
        
        result = await self.user_session_collection.aggregate(pipeline).to_list(length=1)
        return int(result[0]['avgLogin']) if result else 0

    async def getUserAvgLoginSession(self, userID: str) -> Optional[timedelta]:
        start_date = datetime.utcnow() - timedelta(days=self.n_days_before)
        
        pipeline = [
            {"$match": {"user._id": ObjectId(userID), "loginDatetime": {"$gte": start_date}}},
            {"$project": {
                "activeTime": {"$subtract": ["$logoutDatetime", "$loginDatetime"]}
            }},
            {"$group": {"_id": None, "avgCount": {"$avg": "$activeTime"}}}
        ]
        
        result = await self.user_session_collection.aggregate(pipeline).to_list(length=1)
        if not result or result[0].get('avgCount') is None:
            return None
        
        return timedelta(milliseconds=result[0]['avgCount'])

    async def getWorkFlowUsers(self, tenantId: str, sites: List[str], sitedepartments: List[str], 
                                  contractId: str, userRoles: List[UserRoles], userIds: List[str], 
                                  sortOrder: str) -> List[User]:
        query: Dict[str, Any] = {"tenant.tenantId": tenantId}

        if userRoles:
            roles = [role.conditionFields for role in userRoles]
            query["roles.roleName"] = {"$in": roles}

        if contractId:
            query["contracts"] = {"$not": {"$elemMatch": {"_id": contractId}}}

        site_or_clauses = []
        if sites:
            site_or_clauses.append({
                "sites.sites": {"$elemMatch": {"_id": {"$in": sites}, "siteResponsibility.id": {"$ne": None}}}
            })
        
        if sitedepartments:
            dept_or_clauses = []
            for item in sitedepartments:
                site_id, dept_id = item.split("#")
                dept_or_clauses.append({
                    "sites.sites": {
                        "$elemMatch": {
                            "_id": site_id,
                            "departmentList.departments": {
                                "$elemMatch": {"_id": dept_id, "departmentResponsibility.id": {"$ne": None}}
                            }
                        }
                    }
                })
            if dept_or_clauses:
                site_or_clauses.append({"$or": dept_or_clauses})

        if site_or_clauses:
            query["$or"] = query.get("$or", []) + site_or_clauses

        if userIds:
            query["_id"] = {"$nin": userIds}

        sort_direction = DESCENDING if sortOrder.lower() == "desc" else ASCENDING
        
        cursor = self.user_collection.find(query).sort([("name.firstName", sort_direction)])
        return [User(**doc) async for doc in cursor]
    
    async def getAllAccountsPayableByEntity(self, entityId: str) -> List[str]:
        query = {
            "tenant.tenantId": entityId,
            "roles": {"$elemMatch": {"roleName": AppConstants.FINANCE_USER}}
        }
        cursor = self.user_collection.find(query)
        return [user['email']['officialEmail'] async for user in cursor]

    async def getInactiveUsers(self, tenantId: str) -> List[User]:
        query = {
            "tenant.tenantId": tenantId,
            "userType": UserType.CONTRACTED_SERVICE_PROVIDER_USER.value,
            "currentLogin": None,
            "lastLogin": None
        }
        cursor = self.user_collection.find(query)
        return [User(**doc) async for doc in cursor]

    async def getUsersByIdsAndContractsAndSitesAndDepartments(self, tenantId: str, contracts: List[str], userIds: List[str],
                                                              sites: List[str], departments: List[str]) -> List[User]:
        query = {
            "userType": UserType.CONTRACTED_SERVICE_PROVIDER_USER.value,
            "tenant.tenantId": tenantId
        }

        if contracts:
            query["contracts._id"] = {"$in": contracts}
        
        if userIds:
            query["_id"] = {"$in": [ObjectId(uid) for uid in userIds]}

        if sites and not departments:
            query["sites.sites._id"] = {"$in": sites}
        
        if departments and not sites:
            query["sites.sites.departmentList.departments._id"] = {"$in": departments}

        if sites and departments:
            query["sites.sites"] = {
                "$elemMatch": {
                    "_id": {"$in": sites},
                    "departmentList.departments._id": {"$in": departments}
                }
            }
        
        cursor = self.user_collection.find(query)
        return [User(**doc) async for doc in cursor]

    async def getSurrogateUsersByRoles(self, tenantId: str, roles: Set[Role], userId: str) -> List[User]:
        role_ids = [ObjectId(role.id) for role in roles]
        query = {
            "_id": {"$ne": userId},
            "tenant.tenantId": tenantId,
            "isSurrogateEnabled": True,
            "roles._id": {"$all": role_ids}
        }
        cursor = self.user_collection.find(query)
        return [User(**doc) async for doc in cursor]

    async def getCurrentHoldersForIssuer(self, tenantId: str, issuerId: str) -> List[SurrogateLog]:
        now = datetime.now(timezone.utc)
        query = {
            "tenant._id": tenantId, # Assuming tenant is an object with an _id
            "user._id": issuerId,
            "startDate": {"$lte": now},
            "endDate": {"$gte": now}
        }
        cursor = self.surrogate_log_collection.find(query)
        return [SurrogateLog(**doc) async for doc in cursor]

    async def getIssuersForHolder(self, tenantId: str, holderId: str) -> List[SurrogateLog]:
        now = datetime.now(timezone.utc)
        query = {
            "tenant._id": tenantId,
            "surrogate._id": holderId,
            "startDate": {"$lte": now},
            "endDate": {"$gte": now}
        }
        cursor = self.surrogate_log_collection.find(query)
        return [SurrogateLog(**doc) async for doc in cursor]

    async def getUsersForClient(self, tenantId: str, titles: List[str]) -> List[User]:
        query: Dict[str, Any] = {"tenant.tenantId": tenantId}
        if titles:
            query["sites.sites.siteResponsibility"] = {"$exists": True}
            query["sites.sites.siteResponsibility._id"] = {"$in": titles}
        
        cursor = self.user_collection.find(query)
        return [User(**doc) async for doc in cursor]

    async def getUserMetadata(self, tenantId: str, siteId: Optional[str], startDate: str, endDate: str) -> Dict[str, Dict[str, int]]:
        """
        Get comprehensive user metadata with date filtering.
        Migrated from Java getUserMetadata method.
        """
        from datetime import datetime
        
        # Parse dates
        start_date_obj = datetime.strptime(startDate, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
        end_date_obj = datetime.strptime(endDate, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
        
        response_map = {}
        
        # All Registered Users Data
        all_registered_users_map = {}
        query0 = self._getBaseMetaDataQuery(tenantId, siteId)
        query0["userCreatedDate"] = {"$gte": start_date_obj, "$lte": end_date_obj}
        
        all_registered_users_count = await self.user_collection.count_documents(query0)
        
        # Blocked users within date range
        blocked_query0 = query0.copy()
        blocked_query0["isBlocked"] = True
        all_blocked_users = await self.user_collection.count_documents(blocked_query0)
        
        all_registered_users_map["allRegisteredUsersCount"] = all_registered_users_count
        all_registered_users_map["allBlockedUsers"] = all_blocked_users
        response_map["allRegisteredUsers"] = all_registered_users_map
        
        # Registered Users Data
        registered_users_map = {}
        query1 = self._getBaseMetaDataQuery(tenantId, siteId)
        query1["userType"] = UserType.REGISTERED_USER.value
        registered_users_count = await self.user_collection.count_documents(query1)
        
        # Blocked registered users
        blocked_registered_query = query1.copy()
        blocked_registered_query["isBlocked"] = True
        blocked_registered_query["userBlockedOrDeactivatedDate"] = {"$gte": start_date_obj, "$lte": end_date_obj}
        blocked_registered_user_count = await self.user_collection.count_documents(blocked_registered_query)
        
        # New registered users
        new_registered_query = self._getBaseMetaDataQuery(tenantId, siteId)
        new_registered_query["userType"] = UserType.REGISTERED_USER.value
        new_registered_query["userCreatedDate"] = {"$gte": start_date_obj, "$lte": end_date_obj}
        new_registered_users_count = await self.user_collection.count_documents(new_registered_query)
        
        registered_users_map["registeredUsersCount"] = registered_users_count
        registered_users_map["blockedRegisteredUserCount"] = blocked_registered_user_count
        registered_users_map["newRegisteredUsersCount"] = new_registered_users_count
        response_map["registeredUsers"] = registered_users_map
        
        # Contracted Service Provider Users Data
        contracted_service_provider_users_map = {}
        query2 = self._getBaseMetaDataQuery(tenantId, siteId)
        query2["userType"] = UserType.CONTRACTED_SERVICE_PROVIDER_USER.value
        contracted_service_provider_users_count = await self.user_collection.count_documents(query2)
        
        # Blocked contracted service provider users
        blocked_csp_query = query2.copy()
        blocked_csp_query["isBlocked"] = True
        blocked_csp_query["userBlockedOrDeactivatedDate"] = {"$gte": start_date_obj, "$lte": end_date_obj}
        blocked_contracted_service_provider_users_count = await self.user_collection.count_documents(blocked_csp_query)
        
        # New contracted service provider users
        new_csp_query = self._getBaseMetaDataQuery(tenantId, siteId)
        new_csp_query["userType"] = UserType.CONTRACTED_SERVICE_PROVIDER_USER.value
        new_csp_query["userCreatedDate"] = {"$gte": start_date_obj, "$lte": end_date_obj}
        new_contracted_service_provider_users_count = await self.user_collection.count_documents(new_csp_query)
        
        contracted_service_provider_users_map["contractedServiceProviderUsersCount"] = contracted_service_provider_users_count
        contracted_service_provider_users_map["blockedContractedServiceProviderUsersCount"] = blocked_contracted_service_provider_users_count
        contracted_service_provider_users_map["newContractedServiceProviderUsersCount"] = new_contracted_service_provider_users_count
        response_map["contractedServiceProviderUsers"] = contracted_service_provider_users_map
        
        # Deactivated Users Data
        deactivated_users_map = {}
        deactivated_query = self._getBaseMetaDataQuery(tenantId, siteId)
        deactivated_query["isActivated"] = False
        deactivated_query["userBlockedOrDeactivatedDate"] = {"$gte": start_date_obj, "$lte": end_date_obj}
        users_deactivated_in_specified_time_period = await self.user_collection.count_documents(deactivated_query)
        
        deactivated_users_map["usersDeactivatedInSpecifiedTimePeriod"] = users_deactivated_in_specified_time_period
        response_map["deactivatedUsers"] = deactivated_users_map
        
        # Invited Users Data
        invited_users_map = {}
        invited_query = self._getBaseMetaDataQuery(tenantId, siteId)
        invited_query["isInvited"] = True
        invited_query["userCreatedDate"] = {"$gte": start_date_obj, "$lte": end_date_obj}
        invited_users = await self.user_collection.count_documents(invited_query)
        
        # Past due users (users created more than CONSTANTS.DAYS ago)
        past_due_cutoff = datetime.now() - timedelta(days=AppConstants.DAYS)
        past_due_query = self._getBaseMetaDataQuery(tenantId, siteId)
        past_due_query["userCreatedDate"] = {"$lte": past_due_cutoff}
        past_due_users = await self.user_collection.count_documents(past_due_query)
        
        invited_users_map["invitedUsers"] = invited_users
        invited_users_map["pastDueUsers"] = past_due_users
        response_map["invitedUsers"] = invited_users_map
        
        return response_map

    async def getUserSession(self) -> Dict[str, Any]:
        """
        Get user session analytics.
        Migrated from Java getUserSession method.
        """
        start_date = datetime.now() - timedelta(days=self.n_days_before)
        end_date = datetime.now()
        
        # Average login attempt aggregation
        login_attempt_pipeline = [
            {"$match": {"loginDatetime": {"$gte": start_date, "$lte": end_date}}},
            {"$project": {
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$loginDatetime"}}
            }},
            {"$group": {"_id": "$date", "count": {"$sum": 1}}},
            {"$group": {"_id": None, "avgLogin": {"$avg": "$count"}}}
        ]
        
        avg_login_attempt_result = await self.user_session_collection.aggregate(login_attempt_pipeline).to_list(length=1)
        
        # Average session duration aggregation
        session_duration_pipeline = [
            {"$match": {"loginDatetime": {"$gte": start_date, "$lte": end_date}}},
            {"$project": {
                "difftime": {"$subtract": ["$logoutDatetime", "$loginDatetime"]}
            }},
            {"$group": {"_id": None, "diffavgtime": {"$avg": "$difftime"}}}
        ]
        
        avg_session_duration_result = await self.user_session_collection.aggregate(session_duration_pipeline).to_list(length=1)
        
        result = {}
        if avg_login_attempt_result:
            result["avgLoginAttempt"] = avg_login_attempt_result[0].get("avgLogin", 0)
        
        if avg_session_duration_result:
            result["avgSessionDuration"] = avg_session_duration_result[0].get("diffavgtime", 0)
        
        return result
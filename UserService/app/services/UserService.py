from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import hashlib
import uuid
import base64
import os
import asyncio
from pathlib import Path
import httpx
import jwt
import io
import sys

from fastapi import HTTPException, UploadFile, status
from pydantic import BaseModel

# Core imports
from ..core.constants import AppConstants as CONSTANTS
from ..core.config import settings
from ..core.EmailNotification import EmailNotification
from ..core.QueryProcessor import QueryProcessor

# Model imports
from ..models.aggregates.root.User import User
from ..models.aggregates.Department import Department
from ..models.aggregates.Site import Site
from ..models.aggregates.TotalLoginDetails import TotalLoginDetails
from ..models.aggregates.UserContractDetails import UserContractDetails

# DTO imports
from ..models.DTO.BillingInfoDTO import BillingInfoDTO
from ..models.DTO.ChangePasswordDTO import ChangePasswordDTO
from ..models.DTO.EmailDTO import EmailDTO
from ..models.DTO.EntityDTO import EntityDTO
from ..models.DTO.NotificationDTO import NotificationDTO
from ..models.DTO.ProfilePictureDTO import ProfilePictureDTO
from ..models.DTO.RoleDTO import RoleDTO
from ..models.DTO.SurrogateLogDTO import SurrogateLogDTO
from ..models.DTO.UpdatePasswordDTO import UpdatePasswordDTO
from ..models.DTO.UserDTO import UserDTO
from ..models.DTO.UserDTOList import UserDTOList
from ..models.DTO.UserListDTO import UserListDTO
from ..models.DTO.UserPasswordDTO import UserPasswordDTO
from ..models.DTO.UserRoleDTO import UserRoleDTO
from ..models.DTO.UserSsoIdDTO import UserSsoIdDTO

# Entity imports
from ..models.entity.Group import Group
from ..models.entity.ProfilePicture import ProfilePicture
from ..models.entity.Role import Role
from ..models.entity.SurrogateLog import SurrogateLog
from ..models.entity.UserActivationLinkId import UserActivationLinkId
from ..models.entity.UserPassword import UserPassword
from ..models.entity.UserSessions import UserSessions

# Reference object imports
from ..models.reference_object.File import File
from ..models.reference_object.User import User as UserRef

# Value objects imports
from ..models.valueobjects.AccessLevel import AccessLevel
from ..models.valueobjects.ActionBy import ActionBy
from ..models.valueobjects.BillingInfo import BillingInfo
from ..models.valueobjects.BlockOrDeactivateAction import BlockOrDeactivateAction
from ..models.valueobjects.Contract import Contract
from ..models.valueobjects.ContractLite import ContractLite
from ..models.valueobjects.ContractStatus import ContractStatus
from ..models.valueobjects.Email import Email
from ..models.valueobjects.EntityId import EntityId
from ..models.valueobjects.FileType import FileType
from ..models.valueobjects.Name import Name
from ..models.valueobjects.Password import Password
from passlib.context import CryptContext
from ..models.valueobjects.Sites import Sites
from ..models.valueobjects.SsoId import SsoId
from ..models.valueobjects.Tenant import Tenant
from ..models.valueobjects.UserId import UserId
from ..models.valueobjects.UserRoles import UserRoles
from ..models.valueobjects.UserType import UserType

# Repository imports
from ..repositories.GroupRepository import GroupRepository
from ..repositories.MongoRepository import MongoRepository
from ..repositories.ProfilePictureRepository import ProfilePictureRepository
from ..repositories.RoleRepository import RoleRepository
from ..repositories.SurrogateLogRepository import SurrogateLogRepository
from ..repositories.UserActivationLinkIdRepository import UserActivationLinkIdRepository
from ..repositories.UserJobDetailsRepository import UserJobDetailsRepository
from ..repositories.UserPasswordRepository import UserPasswordRepository
from ..repositories.UserRepository import UserRepository
from ..repositories.UserSessionRepository import UserSessionRepository

# Client imports
from ..clients.ContractClient import ContractClient
from ..clients.EntityClient import EntityClient
from ..clients.TimesheetClient import TimesheetClient

# Security imports
from ..security.JwtUtil import JwtUtil
from ..security.OauthJwtDecoder import OauthJwtDecoder
from ..security.SecurityService import SecurityService

# PubSub imports
from ..pubsub.EmailMessageSupplier import EmailMessageSupplier

# Other service imports
from .RoleService import RoleService
from .SurrogateService import SurrogateService

# Make sure the workspace root (containing S3BucketModule) is importable
try:
    ws_root = Path(__file__).resolve().parents[3]
    if str(ws_root) not in sys.path:
        sys.path.insert(0, str(ws_root))
except Exception:
    pass

try:
    # Prefer shared module placed at workspace root
    from S3BucketModule.S3FileTransfer import S3FileTransfer
except Exception:
    # Graceful fallback using boto3 if shared module isn't importable at runtime
    class S3FileTransfer:  # type: ignore
        def __init__(self):
            import boto3  # noqa: F401

        def uploadToS3Bucket(self, region, accessKey, secretKey, bucketName, inputStream, fileName, contentType, fileSize, id):
            import boto3
            s3 = boto3.client(
                's3',
                aws_access_key_id=accessKey,
                aws_secret_access_key=secretKey,
                region_name=region,
            )
            key = f"{id}/{fileName}"
            extra_args = {'ContentType': contentType or 'application/octet-stream', 'ContentLength': fileSize}
            s3.upload_fileobj(inputStream, bucketName, key, ExtraArgs=extra_args)

        def deleteAFile(self, bucketName, fileName, region, accessKey, secretKey):
            import boto3
            s3 = boto3.client(
                's3',
                aws_access_key_id=accessKey,
                aws_secret_access_key=secretKey,
                region_name=region,
            )
            s3.delete_object(Bucket=bucketName, Key=fileName)

        def checkAndReturnFilePreSignedUrl(self, region, accessKey, secretKey, bucketName, filePath, fileUrlexpirationtimeInSeconds=3600):
            import boto3
            s3 = boto3.client(
                's3',
                aws_access_key_id=accessKey,
                aws_secret_access_key=secretKey,
                region_name=region,
            )
            s3.head_object(Bucket=bucketName, Key=filePath)
            return s3.generate_presigned_url('get_object', Params={'Bucket': bucketName, 'Key': filePath}, ExpiresIn=fileUrlexpirationtimeInSeconds)


class UserService:
    """
    User management service handling all user-related operations.
    Converted from Java UserService to Python with camelCase preservation.
    """
    
    def __init__(
        self,
        userRepository: UserRepository,
        profilePictureRepository: ProfilePictureRepository = None,
        queryProcessor: QueryProcessor = None,
        contractClient: ContractClient = None,
        entityClient: EntityClient = None,
        jwtUtil: JwtUtil = None,
        oauthJwtDecoder: OauthJwtDecoder = None,
        timesheetClient: TimesheetClient = None,
        userPasswordRepository: UserPasswordRepository = None,
        userActivationLinkIdRepository: UserActivationLinkIdRepository = None,
        groupRepository: GroupRepository = None,
        roleService: RoleService = None,
        emailMessageSupplier: EmailMessageSupplier = None
    ):
        self.userRepository = userRepository
        self.profilePictureRepository = profilePictureRepository
        self.queryProcessor = queryProcessor
        self.contractClient = contractClient
        self.entityClient = entityClient
        self.jwtUtil = jwtUtil
        self.oauthJwtDecoder = oauthJwtDecoder
        self.timesheetClient = timesheetClient
        self.userPasswordRepository = userPasswordRepository
        self.userActivationLinkIdRepository = userActivationLinkIdRepository
        self.groupRepository = groupRepository
        self.roleService = roleService
        self.emailMessageSupplier = emailMessageSupplier
        
        # Configuration values from settings
        self.ssoURL = settings.SSO_URL
        self.protocol = settings.PROTOCOL
        self.appBaseURL = settings.APP_BASE_URL
        self.appContext = settings.APP_CONTEXT
        self.fileServerPath = settings.FILE_SERVER_PATH
        self.fileServerBaseURL = settings.FILE_SERVER_BASE_URL
        self.bucketName = settings.AWS_BUCKET_NAME
        self.accessKey = settings.AWS_ACCESS_KEY
        self.secretKey = settings.AWS_SECRET_KEY
        self.awsRegion = settings.AWS_REGION
        self.awsBucketUrl = settings.AWS_BUCKET_URL
        # S3 transfer helper (provided by local S3BucketModule)
        self.s3Transfer = S3FileTransfer()
        self.masterEntity = settings.MASTER_ENTITY_NAME

        # Constants
        self.LINK_EXPIRE_TIME = 48 * 60 * 60 * 1000  # 48 hours in milliseconds
        self.PRODUCER_BINDING_NAME = "userProducer-out-0"

        # Instance attributes
        self.tenantId = None
        # Password encoder (BCrypt) to match Java's BCryptPasswordEncoder
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async def createNewUser(self, user: User, authorization: Optional[str] = None) -> User:
        """
        Create a new user with registration validation.
        """
        await self.userRegistrationValidation(user)
        # If ssoId is missing, try to derive from token first
        derived_username: Optional[str] = None
        if authorization is not None:
            try:
                derived_username = await self.extractUserNameFromOauthJwtToken(authorization, {})
            except Exception:
                # Ignore here; validation will later fail if we truly need it
                derived_username = None

        if (not user.ssoId) or (not getattr(user.ssoId, 'id', None)):
            if derived_username:
                user.ssoId = SsoId(id=derived_username)

        ssoId = SsoId(id=user.ssoId.id)
        tenant = user.tenant
        
        userDoc = None
        
        if user.ssoId.id == CONSTANTS.DUMMY_USER_ID:
            userDoc = await self.userRepository.findBySsoIdAndTenant(user.ssoId.id, tenant)
        else:
            userDoc = await self.userRepository.findBySsoId(ssoId)
        
        if user.contracts is not None:
            for contract in user.contracts:
                if contract.contractStatus == ContractStatus.INACTIVE:
                    contract.contractStatus = ContractStatus.ACTIVE
        
        if userDoc is not None:
            existingContracts = list(userDoc.contracts or [])
            newContracts = list(user.contracts or [])
            # Helpers to normalize potential dict/object ids to strings
            def norm_id(val):
                if val is None:
                    return None
                if isinstance(val, dict):
                    for k in ('_id', 'id', '$oid'):
                        if k in val:
                            return str(val[k])
                    return str(val)
                return str(val) if not isinstance(val, (str, int)) else str(val)
            # Merge contracts by normalized id
            seen_contract_ids = {norm_id(getattr(c, 'id', None)) for c in existingContracts if getattr(c, 'id', None) is not None}
            for newContract in newContracts:
                nid_raw = getattr(newContract, 'id', None)
                nid = norm_id(nid_raw)
                if not nid or nid not in seen_contract_ids:
                    existingContracts.append(newContract)
                    if nid:
                        seen_contract_ids.add(nid)
            userDoc.contracts = existingContracts

            # Merge roles as list, deduplicate by (id, roleName)
            if user.roles:
                existingRoles = list(userDoc.roles or [])
                def role_key(r):
                    rid = getattr(r, 'id', None)
                    return (norm_id(rid), getattr(r, 'roleName', None))
                existing_keys = {role_key(r) for r in existingRoles}
                for r in list(user.roles):
                    rk = role_key(r)
                    if rk not in existing_keys:
                        existingRoles.append(r)
                        existing_keys.add(rk)
                userDoc.roles = existingRoles
            return await self.userRepository.save(userDoc)
        
        if user.roles is None:
            user.roles = []
        
        if user.userType is not None and user.userType == UserType.REGISTERED_USER:
            user.isInvited = True
        
        if authorization is not None:
            userName = derived_username or await self.extractUserNameFromOauthJwtToken(authorization, {})
            actionBy = ActionBy(actionByUserId=userName, actionDateTime=datetime.now())
            # In Java, registration sets InvitedBy; align parity here
            user.InvitedBy = actionBy
        
        user = await self.userRepository.save(user)
        
        if (user.userType is not None and 
            user.userType == UserType.REGISTERED_USER and 
            userDoc is None):
            
            entityDTO = await self.entityClient.get_entity_by_id(user.tenant.tenantId)
            entityName = entityDTO.entityName.entityName if entityDTO.entityName else ""
            
            emailNotification = EmailNotification()
            EMAIL_SUBJECT = "User Registration Successful"
            
            templateValue = {
                "fullName": user.name.fullName,
                "entityName": entityName,
                "activationURL": self.generateActivationURL(user, "www")
            }
            
            toAddress = [user.email.officialEmail]
            
            await emailNotification.sendMail(
                self.emailMessageSupplier,
                CONSTANTS.PRODUCER_BINDING_NAME,
                toAddress,
                EMAIL_SUBJECT,
                templateValue,
                None,
                None,
                "userRegistration",
                user.tenant.tenantId
            )
        
        return user

    def generateActivationURL(self, user: User, subdomain: str) -> str:
        """
        Generate activation URL for user.
        """
        uuid_str = str(uuid.uuid4())
        tenantId = user.tenant.tenantId
        self.saveActivationLinkId(uuid_str, user.id, tenantId)
        
        forgetPasswordURL = self.passwordUrlCreation(uuid_str, subdomain)
        return forgetPasswordURL

    def generateSsoIdUpdationURL(self, user: User, subdomain: str) -> str:
        """
        Generate SSO ID updation URL for user.
        """
        uuid_str = str(uuid.uuid4())
        tenantId = user.tenant.tenantId
        self.saveActivationLinkId(uuid_str, user.id, tenantId)
        
        ssoURL = self.ssoUrlCreation(uuid_str, subdomain)
        return ssoURL

    async def forgotPassword(self, email: Email) -> Optional[str]:
        """
        Handle forgot password request.
        """
        user = await self.userRepository.findByEmail(email)
        activationURL = None
        
        if user is not None:
            entityDTO = await self.entityClient.get_entity_by_id(user.tenant.tenantId)
            subdomain = entityDTO.subDomain if hasattr(entityDTO, 'subDomain') else "www"
            activationURL = self.generateActivationURL(user, subdomain)
            
            emailNotification = EmailNotification()
            EMAIL_SUBJECT = "Password Reset Request"
            
            templateValue = {
                "fullName": user.name.fullName,
                "resetURL": activationURL
            }
            
            toAddress = [email.officialEmail]
            
            await emailNotification.sendMail(
                self.emailMessageSupplier,
                CONSTANTS.PRODUCER_BINDING_NAME,
                toAddress,
                EMAIL_SUBJECT,
                templateValue,
                None,
                None,
                "forgotPassword",
                user.tenant.tenantId
            )
        else:
            raise HTTPException(status_code=404, detail="User not found with this email")
        
        return activationURL

    def passwordUrlCreation(self, uuid_str: str, subdomain: str) -> str:
        """
        Create password URL.
        """
        passwordURL = f"{self.protocol}{subdomain}.{self.appBaseURL}{self.appContext}setPassword/{uuid_str}"
        return passwordURL

    def ssoUrlCreation(self, uuid_str: str, subdomain: str) -> str:
        """
        Create SSO URL.
        """
        ssoURL = f"{self.protocol}{subdomain}.{self.appBaseURL}{self.appContext}user/ssoId/{uuid_str}"
        return ssoURL

    def saveActivationLinkId(self, uuidId: str, userId: str, tenantId: str) -> None:
        """
        Save activation link ID.
        """
        userActivationLinkId = UserActivationLinkId()
        userActivationLinkId.userId = userId
        userActivationLinkId.tenantId = tenantId
        
        try:
            messageDigest = hashlib.sha256()
            messageDigest.update(uuidId.encode('utf-8'))
            hashedUuid = messageDigest.hexdigest()
            
            userActivationLinkId.hashedUuid = hashedUuid
            userActivationLinkId.expireTime = datetime.now() + timedelta(milliseconds=self.LINK_EXPIRE_TIME)
            
            self.userActivationLinkIdRepository.save(userActivationLinkId)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save activation link: {str(e)}")

    async def getOrCreateUser(self, userName: str, tenantId: str) -> User:
        """
        Get or create user based on username and tenant.
        """
        isUserAvailableInTenant = await self.checkUserInTenant(userName, tenantId)
        user = None
        
        if not isUserAvailableInTenant:
            user = User()
            user.ssoId = SsoId(id=userName)
            user.tenant = Tenant(tenantId=tenantId)
            user.userType = UserType.CONTRACTED_SERVICE_PROVIDER_USER
            user.isActivated = False
            user.isInvited = False
            user.roles = []
            
            user = await self.userRepository.save(user)
        else:
            tenant = Tenant(tenantId=tenantId)
            user = await self.userRepository.findBySsoIdAndTenant(userName, tenant)
        
        return user

    async def loadUserByEmailId(self, ssoId: str) -> User:
        """
        Load user by email ID.
        """
        user = await self.userRepository.findBySsoIdIgnoreCase(ssoId)
        
        if user is not None:
            return user
        else:
            raise HTTPException(status_code=404, detail="User not found")

    async def resetHashIdAndExpireTime(self, userId: str) -> None:
        """
        Reset hash ID and expire time.
        """
        listOfIds = await self.userActivationLinkIdRepository.getAllIdsByUser(userId)
        await self.userActivationLinkIdRepository.deleteAll(listOfIds)

    def getEncodedPassword(self, password: str) -> Optional[str]:
        """Encode password using BCrypt (same as Java BCryptPasswordEncoder)."""
        if password is None:
            return None
        return self.pwd_context.hash(password)

    async def saveRoleToUser(self, userRoleDTO: UserRoleDTO, tenantId: str) -> None:
        """
        Save role to user.
        """
        email = userRoleDTO.email
        
        # email is already a string (EmailStr), not an object with officialEmail
        # Use findByEmailAndTenant to check if user exists in tenant
        tenant = Tenant(tenantId=tenantId)
        user = await self.userRepository.findByEmailAndTenant(email, tenant)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not available in tenant")
        
        # Update roles
        user.roles = userRoleDTO.roles
        
        await self.userRepository.save(user)

    async def saveUserList(self, userList: List[User]) -> None:
        """
        Save list of users.
        """
        userList = await self.bulkUserRegistrationValidationAndPasswordUpdation(userList)
        await self.userRepository.saveAll(userList)

    async def getUserList(
        self, 
        tenantID: str, 
        firstName: Optional[str] = None,
        lastName: Optional[str] = None,
        contractID: Optional[str] = None,
        activated: Optional[str] = None,
        userType: Optional[str] = None,
        blocked: Optional[str] = None,
        invited: Optional[str] = None,
        partnerId: Optional[str] = None,
        sites: Optional[List[str]] = None,
        titles: Optional[List[str]] = None,
        sitedepartments: Optional[List[str]] = None,
        contractIdOnFile: Optional[str] = None,
        userTypes: Optional[List[str]] = None,
        searchText: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> UserListDTO:
        """
        Get filtered user list.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"getUserList called with tenantID: {tenantID}")
        tenant = Tenant(tenantId=tenantID)
        logger.info(f"Created tenant object: {tenant}")
        
        result = await self.queryProcessor.getFilteredUsers(
            tenant, firstName, lastName, contractID, activated, userType, blocked,
            invited, partnerId, sites, titles, sitedepartments, contractIdOnFile,
            userTypes, searchText, offset, limit
        )
        logger.info(f"QueryProcessor returned result with {len(result.users) if result and result.users else 0} users")
        return result

    async def updateUser(self, user: User, tenantId: str) -> str:
        """
        Update user.
        """
        if user.id is not None:
            # Handle user ID logic
            pass
        
        user = await self.userUpdateValidation(user, tenantId)
        await self.userRepository.save(user)
        return "User Updated Successfully"

    async def checkUserInTenant(self, ssoId: str, tenantId: str) -> bool:
        """
        Check if user exists in tenant.
        """
        tenant = Tenant(tenantId=tenantId)
        userDoc = await self.userRepository.findBySsoIdAndTenant(ssoId, tenant)
        return userDoc is not None

    async def getUserById(self, id: str, tenantId: str) -> Optional[User]:
        """
        Get user by ID.
        Note: Java path uses only the userId for this read; don't filter by tenant here.
        """
        userDoc = await self.userRepository.findById(id)
        return userDoc

    async def getUserByIds(self, userIds: List[str]) -> List[User]:
        """
        Get users by list of IDs.
        """
        users = await self.userRepository.findAllByIdIn(userIds)
        return users

    async def setUserPassword(self, tenantId: str, userPasswordDTO: UserPasswordDTO) -> User:
        """
        Set user password.
        """
        tenant = Tenant(tenantId=tenantId)
        userDoc = await self.userRepository.findByIdAndTenant(userPasswordDTO.userId, tenant)
        
        if userDoc is not None:
            encodedPassword = self.getEncodedPassword(userPasswordDTO.password.password)
            userDoc.password = Password(password=encodedPassword)
            userDoc.isActivated = True
            
            await self.setPasswordInUserPasswordList(userPasswordDTO)
            await self.resetHashIdAndExpireTime(userPasswordDTO.userId)
            # Persist user changes (nested password object)
            saved = await self.userRepository.save(userDoc)

            # Also mirror to legacy root field for backward compatibility:
            # Some existing data/tools expect 'encryptedPassword' at root level.
            try:
                await self.userRepository.updateById(
                    saved.id,
                    {
                        "password": {"encryptedPassword": encodedPassword},
                        "encryptedPassword": encodedPassword,
                        # Ensure activation flag is persisted with internal key naming
                        "isActivated": True,
                    },
                )
            except Exception:
                # Don't fail the flow if the compatibility write has issues
                pass

            return saved
        else:
            raise HTTPException(status_code=404, detail="User not found")

    async def setPasswordInUserPasswordList(self, userPasswordDTO: UserPasswordDTO) -> None:
        """
        Set password in user password list.
        """
        passwordListMaximumSize = 12
        userPasswordDoc = await self.userPasswordRepository.findByUserId(userPasswordDTO.userId)
        
        if userPasswordDoc is not None:
            passwordList = userPasswordDoc.passwordList or []
            
            encodedPassword = self.getEncodedPassword(userPasswordDTO.password.password)
            passwordList.append(encodedPassword)
            
            if len(passwordList) > passwordListMaximumSize:
                passwordList = passwordList[-passwordListMaximumSize:]
            
            userPasswordDoc.passwordList = passwordList
            await self.userPasswordRepository.save(userPasswordDoc)
        else:
            newUserPassword = UserPassword()
            newUserPassword.userId = userPasswordDTO.userId
            newUserPassword.passwordList = [self.getEncodedPassword(userPasswordDTO.password.password)]
            await self.userPasswordRepository.save(newUserPassword)

    async def getUsersByTenantandRole(self, tenantID: str, roleNames: List[str]) -> List[User]:
        """
        Get users by tenant and role.
        """
        tenant = Tenant(tenantId=tenantID)
        # sort = Sort.by(Direction.ASC, "name.firstName")  # TODO: Implement sorting
        return await self.userRepository.getUsersByTenantIDandRole(tenant, roleNames)

    async def userRegistrationValidation(self, user: User) -> None:
        """
        Validate user registration.
        """
        if user.tenant is None:
            raise HTTPException(status_code=400, detail="Tenant cannot be null")
        
        if not user.tenant.tenantId or user.tenant.tenantId.strip() == "":
            raise HTTPException(status_code=400, detail="Tenant ID cannot be blank")

    async def userUpdateValidation(self, user: User, tenantId: str) -> User:
        """
        Validate user update.
        """
        if not user.id or user.id.strip() == "":
            raise HTTPException(status_code=400, detail="User ID cannot be blank")
        
        # Normalize potentially string fields into value objects
        if isinstance(user.email, str):
            user.email = Email(officialEmail=user.email)
        if isinstance(user.tenant, str):
            user.tenant = Tenant(tenantId=user.tenant)
        if user.ssoId is None or isinstance(getattr(user.ssoId, 'id', None), str) is False:
            # if ssoId is a plain string or missing, try to fix from existing or leave for check below
            if isinstance(user.ssoId, str):
                user.ssoId = SsoId(id=user.ssoId)
        
        userDoc = await self.userRepository.findById(user.id)
        if userDoc is None:
            raise HTTPException(status_code=404, detail="User not found")

        # Email checks - guard against None
        if not user.email or not user.email.officialEmail:
            raise HTTPException(status_code=400, detail="Email is required for update")
        if not userDoc.email or not userDoc.email.officialEmail:
            raise HTTPException(status_code=400, detail="Existing user record missing email")
        if userDoc.email.officialEmail != user.email.officialEmail:
            existingUserWithEmail = await self.userRepository.findByEmailAndTenant(user.email, user.tenant)
            if existingUserWithEmail is not None:
                raise HTTPException(status_code=400, detail="Email already exists for another user in this tenant")

        # Tenant membership check should be ID-based to avoid SSO mismatches
        tenant = Tenant(tenantId=tenantId)
        userInTenant = await self.userRepository.findByIdAndTenant(user.id, tenant)
        if userInTenant is None:
            raise HTTPException(status_code=404, detail="User not available in tenant")
        # Keep ssoId presence check for parity, but after membership confirmation
        if not user.ssoId or not user.ssoId.id:
            raise HTTPException(status_code=400, detail="ssoId is required for update")
        
        user.password = userDoc.password
        return user

    async def bulkUserRegistrationValidationAndPasswordUpdation(self, userList: List[User]) -> List[User]:
        """
        Bulk user registration validation and password update.
        """
        emailList = []
        tenantErrorUserList = []
        passwordErrorUserList = []
        
        for user in userList:
            if user.email:
                existingUser = await self.userRepository.findByEmailAndTenant(user.email, user.tenant)
                if existingUser is not None:
                    emailList.append(user.email.officialEmail)
            
            if user.tenant is None or not user.tenant.tenantId or user.tenant.tenantId.strip() == "":
                tenantErrorUserList.append(user.name.fullName if user.name else "Unknown")
            
            if user.password is None or not user.password.password or user.password.password.strip() == "":
                passwordErrorUserList.append(user.name.fullName if user.name else "Unknown")
            else:
                encodedPassword = self.getEncodedPassword(user.password.password)
                user.password = Password(password=encodedPassword)
        
        if len(emailList) > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Users with these emails already exist: {', '.join(emailList)}"
            )
        
        if len(tenantErrorUserList) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Tenant information missing for users: {', '.join(tenantErrorUserList)}"
            )
        
        return userList

    async def getUsersMetadata(self, tenantId: str, siteId: str, startDate: str, endDate: str) -> Dict[str, Dict[str, int]]:
        """
        Get users metadata.
        """
        return await self.queryProcessor.getUserMetadata(tenantId, siteId, startDate, endDate)

    async def getRegisteredUsersMetadata(self, tenantId: str, siteId: str) -> Dict[str, int]:
        """
        Get registered users metadata.
        """
        return await self.queryProcessor.getRegisteredUsersMetadata(tenantId, siteId)

    # blockOrDeactivateUser method moved to camelCase section below with Java-matching signature

    async def saveLoginDateTime(self, ssoId: SsoId, tenantId: str) -> None:
        """
        Save login date time.
        """
        user = await self.userRepository.findBySsoId(ssoId)
        currentLoginDateTime = datetime.now()
        lastLoginDateTime = user.currentLogin
        user.lastLogin = lastLoginDateTime
        user.currentLogin = currentLoginDateTime
        await self.userRepository.save(user)

    async def getUserAvgLoginCount(self, userID: str) -> int:
        """
        Get user average login count.
        """
        return await self.queryProcessor.getUserAvgLoginCount(userID)

    async def getUserAvgLoginSession(self, userID: str) -> timedelta:
        """
        Get user average login session.
        """
        return await self.queryProcessor.getUserAvgLoginSession(userID)

    async def saveLoginDetail(self, ssoId: SsoId, avgLoginCount: int, avgLoginSession: timedelta) -> None:
        """
        Save login detail.
        """
        user = await self.userRepository.findBySsoId(ssoId)
        user.avgLoginCount = avgLoginCount
        user.avgLoginSession = avgLoginSession
        await self.userRepository.save(user)

    async def getUserSession(self) -> Dict[str, Any]:
        """
        Get user session.
        """
        return await self.queryProcessor.getUserSession()

    # changePassword method moved to camelCase section below with Java-matching signature

    async def newPasswordValidation(self, userID: str, newPassword: Password) -> None:
        """
        Validate new password.
        """
        userPasswordDoc = await self.userPasswordRepository.findByUserId(userID)
        rawPassword = newPassword.password
        
        if userPasswordDoc is not None:
            passwordList = userPasswordDoc.passwordList or []
            
            for existingPassword in passwordList:
                if self.checkPassword(rawPassword, existingPassword):
                    raise HTTPException(
                        status_code=400, 
                        detail="New password cannot be same as any of the last 12 passwords"
                    )
        
        if len(rawPassword) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in rawPassword):
            raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in rawPassword):
            raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in rawPassword):
            raise HTTPException(status_code=400, detail="Password must contain at least one number")
    
    def checkPassword(self, rawPassword: str, encodedPassword: str) -> bool:
        """Verify password against stored value.
        - If stored is bcrypt (starts with "$2"), verify with bcrypt.
        - Else support backward compatibility: plain-text equality or SHA-256 equality.
        """
        if not encodedPassword:
            return False
        try:
            if isinstance(encodedPassword, str) and encodedPassword.startswith("$2"):
                return self.pwd_context.verify(rawPassword or "", encodedPassword)
        except Exception:
            # fall through to legacy checks
            pass
        # Legacy: plain text or SHA-256
        if (rawPassword or "") == (encodedPassword or ""):
            return True
        try:
            legacy_sha256 = hashlib.sha256((rawPassword or "").encode("utf-8")).hexdigest()
            return legacy_sha256 == (encodedPassword or "")
        except Exception:
            return False

    async def updatePasswordByUUID(self, tenantId: str, passwordDTO: UpdatePasswordDTO) -> None:
        """
        Update password by UUID.
        """
        uuid_str = passwordDTO.uuid
        
        try:
            messageDigest = hashlib.sha256()
            messageDigest.update(uuid_str.encode('utf-8'))
            hashedUuid = messageDigest.hexdigest()
            
            userActivationLink = await self.userActivationLinkIdRepository.findByHashedUuid(hashedUuid)
            
            if userActivationLink is None:
                raise HTTPException(status_code=404, detail="Invalid or expired activation link")
            
            # Handle expiry: either datetime expireTime or millis linkExpireTime
            now_dt = datetime.now()
            is_expired = False
            if getattr(userActivationLink, 'expireTime', None):
                try:
                    if userActivationLink.expireTime < now_dt:
                        is_expired = True
                except Exception:
                    pass
            elif getattr(userActivationLink, 'linkExpireTime', None):
                try:
                    # linkExpireTime is millis since epoch
                    from datetime import timezone
                    expiry_dt = datetime.fromtimestamp(userActivationLink.linkExpireTime / 1000.0, tz=timezone.utc)
                    if expiry_dt.astimezone(tz=None) < now_dt:
                        is_expired = True
                except Exception:
                    pass
            if is_expired:
                raise HTTPException(status_code=400, detail="Activation link has expired")
            
            if userActivationLink.tenantId != tenantId:
                raise HTTPException(status_code=400, detail="Tenant mismatch")
            
            userPasswordDTO = UserPasswordDTO(
                userId=userActivationLink.userId,
                password=passwordDTO.password
            )
            
            await self.setUserPassword(tenantId, userPasswordDTO)
            # Clear all activation links for this user after successful update
            try:
                listOfIds = await self.userActivationLinkIdRepository.getAllIdsByUser(userActivationLink.userId)
                await self.userActivationLinkIdRepository.deleteAll(listOfIds)
            except Exception:
                pass
            
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail="Password update failed")

    async def addOrUpdateProfilePic(
        self,
        tenantId: str,
        profilePicDTO: ProfilePictureDTO,
        file: UploadFile,
        isUpdate: bool = False
    ) -> str:
        """
        Add or update profile picture.
        """
        userId = profilePicDTO.userId.id
        userDoc = await self.userRepository.findById(userId)
        
        if userDoc is not None:
            if not userDoc.tenant.tenantId == tenantId:
                raise HTTPException(status_code=400, detail="User does not belong to this tenant")
            
            existingProfilePic = await self.profilePictureRepository.findByUserId(profilePicDTO.userId)
            
            if existingProfilePic is not None and isUpdate:
                # Prefer URL to detect S3, but delete by stored key
                if existingProfilePic.filePath or existingProfilePic.fileURL:
                    is_s3 = (existingProfilePic.fileURL or "").startswith("http")
                    if is_s3 and existingProfilePic.filePath:
                        # filePath stores the S3 object key
                        self.deleteFileInBucket(existingProfilePic.filePath)
                    elif existingProfilePic.filePath:
                        # Local filesystem path
                        self.deleteFile(existingProfilePic.filePath)
            
            documentId = self.generateMongoID()
            
            try:
                if self.bucketName and self.accessKey and self.secretKey:
                    filePath, fileURL = await self.saveFileToBucket(file, f"profile-pics/{userId}")
                else:
                    filePath, fileURL = self.saveFile(file, FileType.PROFILE_PICTURE, userId, documentId)
                
                if existingProfilePic is not None:
                    existingProfilePic.filePath = filePath
                    existingProfilePic.fileURL = fileURL
                    existingProfilePic.fileName = file.filename
                    existingProfilePic.fileType = FileType.PROFILE_PICTURE
                    await self.profilePictureRepository.save(existingProfilePic)
                else:
                    newProfilePic = ProfilePicture()
                    newProfilePic.userId = profilePicDTO.userId
                    newProfilePic.filePath = filePath
                    newProfilePic.fileURL = fileURL
                    newProfilePic.fileName = file.filename
                    newProfilePic.fileType = FileType.PROFILE_PICTURE
                    newProfilePic.documentId = documentId
                    await self.profilePictureRepository.save(newProfilePic)
                
                return fileURL
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to save profile picture: {str(e)}")
        else:
            raise HTTPException(status_code=404, detail="User not found")

    @staticmethod
    def generateMongoID() -> str:
        """
        Generate MongoDB-style ID.
        """
        return str(uuid.uuid4())

    def deleteFile(self, path: str) -> None:
        """
        Delete file.
        """
        try:
            os.remove(path)
        except OSError:
            pass

    def saveFile(
        self, 
        file: UploadFile, 
        fileType: FileType, 
        uniqueIdentifier: str, 
        documentId: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Save file to filesystem.
        """
        if documentId is not None:
            directory = os.path.join(self.fileServerPath, fileType.value, documentId)
            fileURL = f"{self.fileServerBaseURL}/{fileType.value}/{documentId}/{file.filename}"
        else:
            directory = os.path.join(self.fileServerPath, fileType.value, uniqueIdentifier)
            fileURL = f"{self.fileServerBaseURL}/{fileType.value}/{uniqueIdentifier}/{file.filename}"
        
        filePath = os.path.join(directory, file.filename)
        
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        try:
            with open(filePath, "wb") as buffer:
                content = file.file.read()
                buffer.write(content)
                file.file.seek(0)
        except Exception as e:
            raise HTTPException(status_code=500, detail="File save failed")
        
        return filePath, fileURL

    async def getProfilePic(self, userId: str) -> Any:
        """
        Get profile picture.
        """
        _userId = UserId(id=userId)
        profilePic = await self.profilePictureRepository.findByUserId(_userId)
        
        if profilePic is None:
            raise HTTPException(status_code=404, detail="Profile picture not found")
        
        return profilePic

    async def getUnInvitedUsersByTenantIDandContract(self, contractId: str) -> List[User]:
        """
        Get uninvited users by tenant ID and contract.
        """
        return await self.userRepository.getUnInvitedUsersByTenantIDandContract(contractId)

    async def saveFileToBucket(self, file: UploadFile, path: str) -> Tuple[str, str]:
        """
        Save file to S3 bucket using the shared S3BucketModule.
        path: S3 prefix (e.g., "profile-pics/<userId>")
        Returns (filePath=S3 key, fileURL=http URL)
        """
        try:
            # Read content and wrap as a stream for upload
            content: bytes = await file.read()
            file.file.seek(0)
            stream = io.BytesIO(content)

            # S3FileTransfer constructs object key as "{id}/{fileName}"
            self.s3Transfer.uploadToS3Bucket(
                self.awsRegion,
                self.accessKey,
                self.secretKey,
                self.bucketName,
                stream,
                file.filename,
                file.content_type or "application/octet-stream",
                len(content),
                path,
            )

            object_key = f"{path}/{file.filename}"
            fileURL = f"{self.awsBucketUrl}/{object_key}"
            return object_key, fileURL
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

    def deleteFileInBucket(self, fileName: str) -> None:
        """
        Delete file in S3 bucket using the shared S3BucketModule.
        fileName is the S3 object key.
        """
        try:
            self.s3Transfer.deleteAFile(
                self.bucketName,
                fileName,
                self.awsRegion,
                self.accessKey,
                self.secretKey,
            )
        except Exception:
            # Swallow exceptions to avoid blocking update flows
            pass

    def getPreSignedUrl(self, filePath: str, expiresInSeconds: int = 3600) -> str:
        """Return a pre-signed URL for an S3 object, if available."""
        try:
            return self.s3Transfer.checkAndReturnFilePreSignedUrl(
                self.awsRegion,
                self.accessKey,
                self.secretKey,
                self.bucketName,
                filePath,
                expiresInSeconds,
            )
        except Exception as e:
            raise HTTPException(status_code=404, detail="File not found or URL generation failed")

    async def getWorkFlowUsers(
        self,
        tenantId: str,
        sites: List[str],
        sitedepartments: List[str],
        contractId: str,
        userRoles: List[UserRoles],
        userIds: List[str],
        sortOrder: str
    ) -> List[User]:
        """
        Get workflow users.
        """
        return await self.queryProcessor.getWorkFlowUsers(
            tenantId, sites, sitedepartments, contractId, userRoles, userIds, sortOrder
        )

    async def extractUserNameFromOauthJwtToken(self, authorization: str, headers: Dict[str, str]) -> str:
        """
        Extract username from JWT.

        Strategy:
        - Prefer RS256 OIDC (Keycloak) validation via OauthJwtDecoder (JWKS from issuer in 'iss').
        - Fallback to HS-based JwtUtil for locally issued tokens.
        """
        raw = authorization[7:] if authorization.startswith("Bearer ") else authorization
        # Try RS256/OIDC first using issuer JWKS
        try:
            # Heuristic: if header alg is RS*, strongly prefer OIDC path
            header = jwt.get_unverified_header(raw)
            alg = (header.get("alg") or "").upper()
            prefer_oidc = alg.startswith("RS")
        except Exception:
            prefer_oidc = True  # if header can't be read, try OIDC first

        # Attempt OIDC decode if preferred
        if prefer_oidc and self.oauthJwtDecoder is not None:
            try:
                claims = self.oauthJwtDecoder.decodeToken(raw)
                userName = (
                    claims.get('preferred_username')
                    or claims.get('userName')
                    or claims.get('sub')
                )
                if not userName:
                    raise HTTPException(status_code=401, detail="Unable to extract username from token")
                return userName
            except Exception:
                # fall through to HS-based attempt
                pass

        # Fallback: HS-based local JWTs
        try:
            claims = self.jwtUtil.getAllClaimsFromToken(raw)
            userName = (
                claims.get('preferred_username')
                or claims.get('userName')
                or claims.get('sub')
            )
            if not userName:
                raise HTTPException(status_code=401, detail="Unable to extract username from token")
            return userName
        except Exception as e:
            import os
            # Optional last resort: allow unverified decode for local/dev
            allow_unverified = os.getenv("OAUTH_DECODE_FALLBACK", "false").lower() == "true" or os.getenv("DEBUG_AUTH", "false").lower() == "true"
            if allow_unverified:
                try:
                    claims = jwt.decode(raw, options={"verify_signature": False})
                    userName = (
                        claims.get('preferred_username')
                        or claims.get('userName')
                        or claims.get('sub')
                    )
                    if not userName:
                        raise HTTPException(status_code=401, detail="Unable to extract username from token")
                    return userName
                except Exception as e2:
                    raise HTTPException(status_code=401, detail=f"Token extraction failed: {e2}")
            # Otherwise, return generic 401
            if os.getenv("DEBUG_AUTH", "false").lower() == "true":
                raise HTTPException(status_code=401, detail=f"Token extraction failed: {e}")
            raise HTTPException(status_code=401, detail="Token extraction failed")

    async def notifyUser(self, userId: str) -> None:
        """
        Notify user.
        """
        doc = await self.userRepository.findById(userId)
        
        if doc is not None:
            entityDTO = await self.entityClient.get_entity_by_id(doc.tenant.tenantId)
            subdomain = entityDTO.subDomain if hasattr(entityDTO, 'subDomain') else "www"
            activationURL = self.generateActivationURL(doc, subdomain)
            
            emailNotification = EmailNotification()
            EMAIL_SUBJECT = "Account Activation Required"
            
            templateValue = {
                "fullName": doc.name.fullName,
                "entityName": entityDTO.entityName.entityName if entityDTO.entityName else "",
                "activationURL": activationURL
            }
            
            toAddress = [doc.email.officialEmail]
            
            await emailNotification.sendMail(
                self.emailMessageSupplier,
                CONSTANTS.PRODUCER_BINDING_NAME,
                toAddress,
                EMAIL_SUBJECT,
                templateValue,
                None,
                None,
                "userNotification",
                doc.tenant.tenantId
            )

    async def notifyEntityUser(self, userId: str) -> None:
        """
        Notify entity user.
        """
        doc = await self.userRepository.findById(userId)
        
        if doc is not None:
            entityDTO = await self.entityClient.get_entity_by_id(doc.tenant.tenantId)
            
            emailNotification = EmailNotification()
            EMAIL_SUBJECT = "Entity User Notification"
            
            templateValue = {
                "fullName": doc.name.fullName,
                "entityName": entityDTO.entityName.entityName if entityDTO.entityName else "",
                "loginURL": self.domainUrlCreation("www")
            }
            
            toAddress = [doc.email.officialEmail]
            
            await emailNotification.sendMail(
                self.emailMessageSupplier,
                CONSTANTS.PRODUCER_BINDING_NAME,
                toAddress,
                EMAIL_SUBJECT,
                templateValue,
                None,
                None,
                "entityUserNotification",
                doc.tenant.tenantId
            )

    async def updateUserList(self, userDTOList: List[UserDTO], tenantId: str) -> None:
        """
        Update user list.
        """
        if userDTOList:
            for userDTO in userDTOList:
                existingUser = await self.userRepository.findById(userDTO.id)
                
                if existingUser is not None:
                    if userDTO.name:
                        existingUser.name = userDTO.name
                    if userDTO.email:
                        existingUser.email = userDTO.email
                    if userDTO.title:
                        existingUser.title = userDTO.title
                    if userDTO.communication:
                        existingUser.communication = userDTO.communication
                    if userDTO.address:
                        existingUser.address = userDTO.address
                    if userDTO.roles is not None:
                        existingUser.roles = userDTO.roles
                    if userDTO.sites:
                        existingUser.sites = userDTO.sites
                    if userDTO.contracts:
                        existingUser.contracts = userDTO.contracts
                    
                    existingUser.isActivated = userDTO.isActivated
                    existingUser.isBlocked = userDTO.isBlocked
                    existingUser.isInvited = userDTO.isInvited
                    
                    await self.userRepository.save(existingUser)

    async def remindContractors(self, userId: str) -> None:
        """
        Remind contractors.
        """
        doc = await self.userRepository.findById(userId)
        
        if doc is not None:
            entityDTO = await self.entityClient.get_entity_by_id(doc.tenant.tenantId)
            
            emailNotification = EmailNotification()
            EMAIL_SUBJECT = "Contractor Reminder"
            
            templateValue = {
                "fullName": doc.name.fullName,
                "entityName": entityDTO.entityName.entityName if entityDTO.entityName else "",
                "reminderMessage": "Please complete your pending tasks and submit your timesheet."
            }
            
            toAddress = [doc.email.officialEmail]
            
            await emailNotification.sendMail(
                self.emailMessageSupplier,
                CONSTANTS.PRODUCER_BINDING_NAME,
                toAddress,
                EMAIL_SUBJECT,
                templateValue,
                None,
                None,
                "contractorReminder",
                doc.tenant.tenantId
            )

    async def getAllAccountsPayableByEntity(self, entityId: str) -> List[str]:
        """
        Get all accounts payable by entity.
        """
        return await self.queryProcessor.getAllAccountsPayableByEntity(entityId)

    def domainUrlCreation(self, subdomain: str) -> str:
        """
        Create domain URL.
        """
        domainURL = f"{self.protocol}{subdomain}.{self.appBaseURL}"
        return domainURL

    async def updateBillingInformation(self, userId: str, tenantId: str, billingInformation: BillingInfoDTO) -> int:
        """
        Update billing information.
        """
        tenant = Tenant(tenantId=tenantId)
        userDoc = await self.userRepository.findByIdAndTenant(userId, tenant)
        
        if userDoc is not None:
            # Map DTO (name, email, mobileNumber) to domain BillingInfo
            email_vo = None
            if getattr(billingInformation, "email", None):
                try:
                    email_vo = Email(officialEmail=str(billingInformation.email))
                except Exception:
                    email_vo = None

            billingInfo = BillingInfo(
                name=getattr(billingInformation, "name", None),
                email=email_vo,
                mobileNumber=getattr(billingInformation, "mobileNumber", None),
            )

            # Persist in the correct user field per model: professionalServicesBilling
            userDoc.professionalServicesBilling = billingInfo
            await self.userRepository.save(userDoc)
            
            return status.HTTP_200_OK
        
        return status.HTTP_400_BAD_REQUEST

    async def updateUserSsoIdByUUID(self, userSsoIdDTO: UserSsoIdDTO) -> None:
        """
        Update user SSO ID by UUID.
        """
        uuid_str = userSsoIdDTO.uuid
        
        try:
            messageDigest = hashlib.sha256()
            messageDigest.update(uuid_str.encode('utf-8'))
            hashedUuid = messageDigest.hexdigest()
            
            userActivationLink = await self.userActivationLinkIdRepository.findByHashedUuid(hashedUuid)
            
            if userActivationLink is None:
                raise HTTPException(status_code=404, detail="Invalid or expired activation link")
            
            if userActivationLink.expireTime < datetime.now():
                raise HTTPException(status_code=400, detail="Activation link has expired")
            
            user = await self.userRepository.findById(userActivationLink.userId)
            
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")
            
            existingUserWithSsoId = await self.userRepository.findBySsoIdAndTenant(
                userSsoIdDTO.ssoId, user.tenant
            )
            
            if existingUserWithSsoId is not None and existingUserWithSsoId.id != user.id:
                raise HTTPException(status_code=400, detail="SSO ID already exists for another user")
            
            user.ssoId = SsoId(id=userSsoIdDTO.ssoId)
            await self.userRepository.save(user)
            
            await self.resetHashIdAndExpireTime(userActivationLink.userId)
            await self.notifySsoIdSetup(user)
            
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail="SSO ID update failed")

    async def notifySsoIdSetup(self, user: User) -> None:
        """
        Notify SSO ID setup.
        """
        entityDTO = await self.entityClient.get_entity_by_id(user.tenant.tenantId)
        entityName = entityDTO.entityName.entityName
        
        emailNotification = EmailNotification()
        EMAIL_SUBJECT = "SSO Id setup completed successfully"
        
        templateValue = {
            "fullName": user.name.fullName,
            "entityName": entityName,
            "ssoId": user.ssoId.id
        }
        
        toAddress = []
        
        if entityDTO.logo is not None and entityDTO.logo.file is not None:
            # Handle logo logic
            pass
        else:
            # Handle default logo logic
            pass
        
        await emailNotification.sendMail(
            self.emailMessageSupplier,
            CONSTANTS.PRODUCER_BINDING_NAME,
            toAddress,
            EMAIL_SUBJECT,
            templateValue,
            None,
            None,
            "ssoIdSetup",
            user.tenant.tenantId
        )

    async def getInactiveUsers(self, tenantId: str, ssoIdAvailable: bool) -> List[User]:
        """
        Get inactive users.
        """
        users = await self.queryProcessor.getInactiveUsers(tenantId)
        inactiveUsers = []
        
        if not ssoIdAvailable:
            for user in users:
                if user.ssoId is None or not user.ssoId.id or user.ssoId.id.strip() == "":
                    inactiveUsers.append(user)
        else:
            for user in users:
                if user.ssoId is not None and user.ssoId.id and user.ssoId.id.strip() != "":
                    daysSinceLastLogin = 0
                    if user.lastLogin:
                        daysSinceLastLogin = (datetime.now() - user.lastLogin).days
                    
                    if daysSinceLastLogin >= 30:
                        inactiveUsers.append(user)
        
        return inactiveUsers

    async def remindInactiveUsersToLogin(self, userIds: List[str]) -> None:
        """
        Remind inactive users to login.
        """
        users = await self.userRepository.findAllByIdIn(userIds)
        
        for user in users:
            entityDTO = await self.entityClient.get_entity_by_id(user.tenant.tenantId)
            
            emailNotification = EmailNotification()
            EMAIL_SUBJECT = "Reminder: Please login to your account"
            
            templateValue = {
                "fullName": user.name.fullName,
                "entityName": entityDTO.entityName.entityName if entityDTO.entityName else "",
                "loginURL": self.domainUrlCreation("www"),
                "daysSinceLastLogin": (datetime.now() - user.lastLogin).days if user.lastLogin else "N/A"
            }
            
            toAddress = [user.email.officialEmail]
            
            await emailNotification.sendMail(
                self.emailMessageSupplier,
                CONSTANTS.PRODUCER_BINDING_NAME,
                toAddress,
                EMAIL_SUBJECT,
                templateValue,
                None,
                None,
                "inactiveUserLoginReminder",
                user.tenant.tenantId
            )

    async def remindInactiveUsersToSetSsoId(self, userIds: List[str]) -> None:
        """
        Remind inactive users to set SSO ID.
        """
        users = await self.userRepository.findAllByIdIn(userIds)
        
        for user in users:
            entityDTO = await self.entityClient.get_entity_by_id(user.tenant.tenantId)
            subdomain = entityDTO.subDomain if hasattr(entityDTO, 'subDomain') else "www"
            ssoSetupURL = self.generateSsoIdUpdationURL(user, subdomain)
            
            emailNotification = EmailNotification()
            EMAIL_SUBJECT = "Reminder: Please set up your SSO ID"
            
            templateValue = {
                "fullName": user.name.fullName,
                "entityName": entityDTO.entityName.entityName if entityDTO.entityName else "",
                "ssoSetupURL": ssoSetupURL
            }
            
            toAddress = [user.email.officialEmail]
            
            await emailNotification.sendMail(
                self.emailMessageSupplier,
                CONSTANTS.PRODUCER_BINDING_NAME,
                toAddress,
                EMAIL_SUBJECT,
                templateValue,
                None,
                None,
                "ssoIdSetupReminder",
                user.tenant.tenantId
            )

    async def getUnInvitedAggregatorUserByTenantIDandContract(self, contractId: str) -> List[User]:
        """
        Get uninvited aggregator user by tenant ID and contract.
        """
        return await self.userRepository.getUnInvitedAggregatorUserByTenantIDandContract(
            contractId, CONSTANTS.ACTIVITY_LOGGER
        )

    async def getUserByIdsAndContractsAndSitesAndDepartments(
        self,
        tenantId: str,
        contracts: List[str],
        userIds: List[str],
        sites: List[str],
        departments: List[str]
    ) -> List[User]:
        """
        Get users by IDs, contracts, sites and departments.
        """
        return await self.queryProcessor.getUsersByIdsAndContractsAndSitesAndDepartments(
            tenantId, contracts, userIds, sites, departments
        )

    async def getNonEntityAccessWorkflowUsers(self, tenantId: str, authorization: str) -> List[User]:
        """
        Get non-entity access workflow users.
        """
        accessLevel = self.jwtUtil.getUserAccessLevelFromToken(authorization)
        userId = self.jwtUtil.getUserIdFromToken(authorization)
        
        if accessLevel == AccessLevel.ENTITY.value:
            tenant = Tenant(tenantId=tenantId)
            return await self.userRepository.findByTenant(tenant)
        
        user = await self.userRepository.findById(userId)
        return [user]

    async def updateUsersContractStatus(self, contract: ContractLite) -> None:
        """
        Update users contract status.
        """
        users = await self.userRepository.getUsersByContractId(contract.id)
        
        for user in users:
            if user.contracts:
                for userContract in user.contracts:
                    if userContract.id == contract.id:
                        userContract.contractStatus = contract.contractStatus
                        break
        
        await self.userRepository.saveAll(users)

    async def updateRenewedContractInUser(self, oldContractId: str, newContractId: str) -> None:
        """
        Update renewed contract in user.
        """
        users = await self.userRepository.getUsersByContractId(oldContractId)
        
        for user in users:
            if user.contracts:
                for userContract in user.contracts:
                    if userContract.id == oldContractId:
                        userContract.id = newContractId
                        break
        
        await self.userRepository.saveAll(users)

    async def createNewUserFromScimResource(self, resource: Any) -> None:
        """
        Create new user from SCIM resource.
        """
        newUser = User()
        tenant = Tenant(tenantId=self.tenantId)
        newUser.tenant = tenant
        newUser.isActivated = getattr(resource, 'active', newUser.isActivated)
        newUser.userType = UserType.CONTRACTED_SERVICE_PROVIDER_USER
        newUser.isInvited = True
        
        if hasattr(resource, 'userName') and resource.userName:
            newUser.ssoId = SsoId(id=resource.userName)
        
        if hasattr(resource, 'name') and resource.name:
            if hasattr(resource.name, 'givenName') and hasattr(resource.name, 'familyName'):
                newUser.name = Name(
                    firstName=resource.name.givenName,
                    lastName=resource.name.familyName
                )
        
        if hasattr(resource, 'emails') and resource.emails:
            for email in resource.emails:
                if hasattr(email, 'value'):
                    newUser.email = Email(officialEmail=email.value)
                    break
        
        if hasattr(resource, 'meta') and resource.meta:
            if hasattr(resource.meta, 'created'):
                newUser.userCreatedDate = resource.meta.created
        
        if newUser.ssoId is not None and newUser.ssoId.id:
            existingUser = await self.userRepository.findBySsoIdAndTenant(newUser.ssoId.id, tenant)
            if existingUser is None:
                await self.userRepository.save(newUser)

    async def getUserForScimById(self, id: str) -> Any:
        """
        Get user for SCIM by ID.
        """
        user = await self.userRepository.findById(id)
        if user is None:
            return None
        
        userResource = {
            "id": user.id,
            "userName": user.ssoId.id if user.ssoId else "",
            "active": user.isActivated,
            "name": {
                "givenName": user.name.firstName if user.name else "",
                "familyName": user.name.lastName if user.name else ""
            },
            "emails": [
                {
                    "value": user.email.officialEmail if user.email else "",
                    "primary": True
                }
            ],
            "meta": {
                "resourceType": "User",
                "created": user.userCreatedDate.isoformat() if user.userCreatedDate else None,
                "lastModified": user.userCreatedDate.isoformat() if user.userCreatedDate else None
            }
        }
        
        return userResource

    async def updateUserByScimResource(self, resource: Any) -> None:
        """
        Update user by SCIM resource.
        """
        if not hasattr(resource, 'id') or not resource.id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        user = await self.userRepository.findById(resource.id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        if hasattr(resource, 'active'):
            user.isActivated = resource.active
        
        if hasattr(resource, 'userName'):
            user.ssoId = SsoId(id=resource.userName)
        
        if hasattr(resource, 'name') and resource.name:
            if hasattr(resource.name, 'givenName') or hasattr(resource.name, 'familyName'):
                user.name = Name(
                    firstName=getattr(resource.name, 'givenName', user.name.firstName if user.name else ""),
                    lastName=getattr(resource.name, 'familyName', user.name.lastName if user.name else "")
                )
        
        if hasattr(resource, 'emails') and resource.emails:
            for email in resource.emails:
                if hasattr(email, 'value'):
                    user.email = Email(officialEmail=email.value)
                    break
        
        await self.userRepository.save(user)

    async def deleteUserByScimId(self, id: str) -> None:
        """
        Delete user by SCIM ID.
        """
        user = await self.userRepository.findById(id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        await self.userRepository.delete(user)

    async def createGroupFromScimResource(self, resource: Any) -> Any:
        """
        Create group from SCIM resource.
        """
        newGroup = Group()
        newGroup.tenantId = self.tenantId
        
        if hasattr(resource, 'displayName'):
            newGroup.displayName = resource.displayName
        
        if hasattr(resource, 'members') and resource.members:
            members = []
            for member in resource.members:
                if hasattr(member, 'value'):
                    user = await self.userRepository.findById(member.value)
                    if user:
                        members.append({
                            "userId": user.id,
                            "userName": user.ssoId.id if user.ssoId else ""
                        })
            newGroup.members = members
        
        savedGroup = await self.groupRepository.save(newGroup)
        
        groupResource = {
            "id": savedGroup.id,
            "displayName": savedGroup.displayName,
            "members": savedGroup.members or [],
            "meta": {
                "resourceType": "Group",
                "created": datetime.now().isoformat(),
                "lastModified": datetime.now().isoformat()
            }
        }
        
        return groupResource

    async def getScimGroupById(self, id: str) -> Any:
        """
        Get SCIM group by ID.
        """
        group = await self.groupRepository.findById(id)
        if group is None:
            return None
        
        groupResource = {
            "id": group.id,
            "displayName": group.displayName,
            "members": group.members or [],
            "meta": {
                "resourceType": "Group",
                "created": group.createdDate.isoformat() if hasattr(group, 'createdDate') and group.createdDate else None,
                "lastModified": group.lastModifiedDate.isoformat() if hasattr(group, 'lastModifiedDate') and group.lastModifiedDate else None
            }
        }
        
        return groupResource

    async def updateScimGroup(self, resourceToUpdate: Any) -> Any:
        """
        Update SCIM group.
        """
        if not hasattr(resourceToUpdate, 'id') or not resourceToUpdate.id:
            raise HTTPException(status_code=400, detail="Group ID is required")
        
        group = await self.groupRepository.findById(resourceToUpdate.id)
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        
        if hasattr(resourceToUpdate, 'displayName'):
            group.displayName = resourceToUpdate.displayName
        
        if hasattr(resourceToUpdate, 'members'):
            existingMembers = group.members or []
            await self.updateSiteAndRoleForGroupMembers(existingMembers, group)
            
            newMembers = []
            if resourceToUpdate.members:
                for member in resourceToUpdate.members:
                    if hasattr(member, 'value'):
                        user = await self.userRepository.findById(member.value)
                        if user:
                            newMembers.append({
                                "userId": user.id,
                                "userName": user.ssoId.id if user.ssoId else ""
                            })
            
            group.members = newMembers
        
        savedGroup = await self.groupRepository.save(group)
        
        groupResource = {
            "id": savedGroup.id,
            "displayName": savedGroup.displayName,
            "members": savedGroup.members or [],
            "meta": {
                "resourceType": "Group",
                "lastModified": datetime.now().isoformat()
            }
        }
        
        return groupResource

    async def updateSiteAndRoleForGroupMembers(self, existingMembers: List[Any], group: Group) -> None:
        """
        Update site and role for group members.
        """
        if existingMembers:
            for member in existingMembers:
                if isinstance(member, dict) and 'userId' in member:
                    user = await self.userRepository.findById(member['userId'])
                    if user and group.sites:
                        if user.sites:
                            for groupSite in group.sites:
                                user.sites = [site for site in user.sites if site.id != groupSite.id]
                        
                        if group.roles and user.roles:
                            for groupRole in group.roles:
                                user.roles = [r for r in user.roles if not (r.id == groupRole.id and r.roleName == groupRole.roleName)]
                        
                        await self.userRepository.save(user)

    async def updateUserRoleAndSite(
        self,
        currentMembers: List[Any],
        siteList: List[Site],
        roles: List[Role],
        existingMembers: List[Any],
        userType: UserType
    ) -> None:
        """
        Update user role and site.
        """
        for member in currentMembers:
            if isinstance(member, dict) and 'userId' in member:
                user = await self.userRepository.findById(member['userId'])
                if user:
                    user.userType = userType
                    
                    if siteList:
                        if user.sites is None:
                            user.sites = Sites(sites=[])
                        
                        for site in siteList:
                            if site not in user.sites.sites:
                                user.sites.sites.append(site)
                    
                    if roles:
                        if user.roles is None:
                            user.roles = []
                        for role in roles:
                            if not any((r.id == role.id and r.roleName == role.roleName) for r in user.roles):
                                user.roles.append(role)
                    
                    await self.userRepository.save(user)

    async def removeSitesForExistingMembers(
        self,
        existingMembers: List[Any],
        siteList: List[Site],
        roles: List[Role]
    ) -> None:
        """
        Remove sites for existing members.
        """
        for member in existingMembers:
            if isinstance(member, dict) and 'userId' in member:
                user = await self.userRepository.findById(member['userId'])
                if user:
                    if siteList and user.sites:
                        for site in siteList:
                            user.sites.sites = [s for s in user.sites.sites if s.id != site.id]
                    
                    if roles and user.roles:
                        for role in roles:
                            user.roles = [r for r in user.roles if not (r.id == role.id and r.roleName == role.roleName)]
                    
                    await self.userRepository.save(user)

    async def deleteScimGroupById(self, id: str) -> None:
        """
        Delete SCIM group by ID.
        """
        group = await self.groupRepository.findById(id)
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        
        if group.members:
            await self.updateSiteAndRoleForGroupMembers(group.members, group)
        
        await self.groupRepository.delete(group)

    async def getScimGroupList(self) -> List[Any]:
        """
        Get SCIM group list.
        """
        groups = await self.groupRepository.findByTenantId(self.tenantId)
        groupList = []
        
        for group in groups:
            groupResource = {
                "id": group.id,
                "displayName": group.displayName,
                "members": group.members or [],
                "meta": {
                    "resourceType": "Group"
                }
            }
            groupList.append(groupResource)
        
        return groupList

    async def getScimGroupByGroup(self, group: Group) -> Any:
        """
        Get SCIM group by group.
        """
        groupResource = {
            "id": group.id,
            "displayName": group.displayName,
            "members": group.members or [],
            "meta": {
                "resourceType": "Group",
                "created": group.createdDate.isoformat() if hasattr(group, 'createdDate') and group.createdDate else None,
                "lastModified": group.lastModifiedDate.isoformat() if hasattr(group, 'lastModifiedDate') and group.lastModifiedDate else None
            }
        }
        
        return groupResource

    async def getUserScimList(self) -> List[Any]:
        """
        Get user SCIM list.
        """
        tenant = Tenant(tenantId=self.tenantId)
        users = await self.userRepository.findByTenant(tenant)
        userList = []
        
        for user in users:
            userResource = {
                "id": user.id,
                "userName": user.ssoId.id if user.ssoId else "",
                "active": user.isActivated,
                "name": {
                    "givenName": user.name.firstName if user.name else "",
                    "familyName": user.name.lastName if user.name else ""
                },
                "emails": [
                    {
                        "value": user.email.officialEmail if user.email else "",
                        "primary": True
                    }
                ],
                "meta": {
                    "resourceType": "User"
                }
            }
            userList.append(userResource)
        
        return userList

    async def getUserForScimByUser(self, user: User) -> Any:
        """
        Get user for SCIM by user.
        """
        userResource = {
            "id": user.id,
            "userName": user.ssoId.id if user.ssoId else "",
            "active": user.isActivated,
            "name": {
                "givenName": user.name.firstName if user.name else "",
                "familyName": user.name.lastName if user.name else ""
            },
            "emails": [
                {
                    "value": user.email.officialEmail if user.email else "",
                    "primary": True
                }
            ],
            "meta": {
                "resourceType": "User",
                "created": user.userCreatedDate.isoformat() if user.userCreatedDate else None
            }
        }
        
        return userResource

    async def getTenantId(self, realm: str) -> None:
        """
        Get tenant ID from realm.
        """
        entityDTO = await self.entityClient.get_entity_by_realm(realm)
        if entityDTO:
            self.tenantId = entityDTO.id
        else:
            raise HTTPException(status_code=404, detail="Tenant not found for realm")

    def setTenantId(self) -> None:
        """
        Set tenant ID.
        """
        if not self.tenantId:
            self.tenantId = self.masterEntity

    async def getMySurrogate(self, tenantId: str, userId: str) -> List[User]:
        """
        Get my surrogate users.
        """
        user = await self.getUserById(userId, tenantId)
        if user and hasattr(user, 'surrogateUsers'):
            return user.surrogateUsers or []
        return []

    async def checkAndRemoveContractUser(self, contractId: str) -> None:
        """
        Check and remove contract user.
        """
        users = await self.userRepository.getUsersByContractId(contractId)
        
        for user in users:
            if user.contracts:
                user.contracts = [c for c in user.contracts if c.id != contractId]
                
                if not user.contracts and user.userType == UserType.CONTRACTED_SERVICE_PROVIDER_USER:
                    await self.userRepository.delete(user)
                else:
                    await self.userRepository.save(user)

    async def getSurrogateForUser(self, userId: str, tenantId: str) -> User:
        """
        Get surrogate for user.
        """
        user = await self.getUserById(userId, tenantId)
        if user and hasattr(user, 'surrogateUser'):
            return user.surrogateUser
        return None

    async def checkAndRemoveContractFromDummyUser(self, user: User) -> None:
        """
        Check and remove contract from dummy user.
        """
        if user.ssoId and user.ssoId.id == CONSTANTS.DUMMY_USER_ID:
            if user.contracts and len(user.contracts) == 1:
                contractToRemove = user.contracts[0]
                user.contracts = []
                await self.userRepository.save(user)

    async def updateScimGroupUsers(self, tenantId: str, groupIds: List[str]) -> str:
        """
        Update SCIM group users.
        """
        self.tenantId = tenantId
        
        for groupId in groupIds:
            group = await self.groupRepository.findById(groupId)
            if group and group.members:
                for member in group.members:
                    if isinstance(member, dict) and 'userId' in member:
                        user = await self.userRepository.findById(member['userId'])
                        if user:
                            if group.sites and user.sites:
                                for site in group.sites:
                                    if site not in user.sites.sites:
                                        user.sites.sites.append(site)
                            
                            if group.roles and user.roles is not None:
                                for role in group.roles:
                                    if not any((r.id == role.id and r.roleName == role.roleName) for r in user.roles):
                                        user.roles.append(role)
                            
                            await self.userRepository.save(user)
        
        return "Group users updated successfully"

    async def getUsersForClient(self, tenantId: str, titles: List[str]) -> List[User]:
        """
        Get users for client.
        """
        tenant = Tenant(tenantId=tenantId)
        users = await self.userRepository.findByTenant(tenant)
        
        if titles:
            filteredUsers = []
            for user in users:
                if user.title and user.title.title in titles:
                    filteredUsers.append(user)
            return filteredUsers
        
        return users

    async def detachContractsFromUser(self, userId: str, contractId: str) -> Dict[str, Any]:
        """
        Detach contracts from user.
        """
        user = await self.userRepository.findById(userId)
        
        if user is None:
            return {"status": "error", "message": "User not found"}
        
        if user.contracts:
            originalContractCount = len(user.contracts)
            user.contracts = [c for c in user.contracts if c.id != contractId]
            
            if len(user.contracts) < originalContractCount:
                await self.userRepository.save(user)
                return {"status": "success", "message": "Contract detached successfully"}
            else:
                return {"status": "error", "message": "Contract not found for this user"}
        
        return {"status": "error", "message": "User has no contracts"}

    # Removed legacy SHA-256 getEncodedPassword; using BCrypt above

    # ===== MISSING METHODS FROM JAVA IMPLEMENTATION =====
    # Adding missing methods to match Java UserService exactly
    
    async def registerNewUser(self, authorization: str, userDTO: UserDTO) -> User:
        """
        Register new user - equivalent to Java registerNewUser method.
        Java: public ResponseEntity<?> registerNewUser(@RequestHeader(value = "X-Authorization") String authorization,@RequestBody UserDTO userDTO)
        """
        try:
            # Build domain User from DTO to ensure required fields are present and aliases are handled
            user = userDTO.to_domain()
            # Call createNewUser with authorization
            return await self.createNewUser(user, authorization)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"User registration failed: {str(e)}")

    async def registerNewUserList(self, userDTOList: UserDTOList) -> str:
        """
        Register new user list - equivalent to Java registerNewUserList method.
        Java: public ResponseEntity<String> registerNewUserList(@RequestBody UserDTOList userDTOList)
        """
        try:
            if not userDTOList.users or len(userDTOList.users) == 0:
                raise HTTPException(status_code=400, detail="User list cannot be empty")
            
            userList = []
            for userDTO in userDTOList.users:
                user = userDTO.to_domain()
                userList.append(user)
            
            await self.saveUserList(userList)
            return f"Successfully registered {len(userList)} users"
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Bulk user registration failed: {str(e)}")

    async def getUserListById(self, tenantId: str, userId: str) -> User:
        """
        Get user list by ID - equivalent to Java getUserListById method.
        Java: public User getUserListById(@RequestHeader(value = "X-tenantID") String tenantId, @PathVariable(name = "userId") String userId)
        """
        # Match Java: lookup by id only (tenant header is accepted but not used for filtering)
        user = await self.userRepository.findById(userId)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def getUserListByListOfId(self, userIds: List[str]) -> List[User]:
        """
        Get user list by list of IDs - equivalent to Java getUserListByListOfId method.
        Java: public List<User> getUserListByListOfId(@RequestParam(name = "userIds") List<String> userIds)
        """
        return await self.getUserByIds(userIds)

    async def getUserListByListOfIdAndContractAndSiteAndDepartment(
        self,
        tenantId: str,
        contracts: Optional[List[str]] = None,
        users: Optional[List[str]] = None,
        sites: Optional[List[str]] = None,
        departments: Optional[List[str]] = None
    ) -> List[User]:
        """
        Get user list by list of ID and contract and site and department - equivalent to Java method.
        Java: public List<User> getUserListByListOfIdAndContractAndSiteAndDepartment(...)
        """
        return await self.getUserByIdsAndContractsAndSitesAndDepartments(
            tenantId, contracts or [], users or [], sites or [], departments or []
        )

    async def addRoleToUser(self, userRoleDTO: UserRoleDTO, tenantId: str) -> str:
        """
        Add role to user - equivalent to Java addRoleToUser method.
        Java: public ResponseEntity<String> addRoleToUser(@RequestBody UserRoleDTO userRoleDTO , @RequestHeader(value = "X-tenantID") String tenantId)
        """
        try:
            await self.saveRoleToUser(userRoleDTO, tenantId)
            return "Role added successfully to user"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to add role to user: {str(e)}")

    async def getUserListByRole(self, tenantId: str, roleNames: List[str]) -> List[User]:
        """
        Get user list by role - equivalent to Java getUserListByRole method.
        Java: public List<User> getUserListByRole(@RequestHeader(value = "X-tenantID") String tenantId, @RequestParam(name = "role") List<String> roleName)
        """
        return await self.getUsersByTenantandRole(tenantId, roleNames)

    async def AddPicByUserId(self, tenantId: str, profilePicDTO: ProfilePictureDTO, file: UploadFile) -> str:
        """
        Add picture by user ID - equivalent to Java AddPicByUserId method.
        Java: public ResponseEntity<String> AddPicByUserId(...)
        """
        try:
            fileURL = await self.addOrUpdateProfilePic(tenantId, profilePicDTO, file, isUpdate=False)
            return f"Profile picture added successfully: {fileURL}"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to add profile picture: {str(e)}")

    async def UpdatePicByUserId(self, tenantId: str, profilePicDTO: ProfilePictureDTO, file: UploadFile) -> str:
        """
        Update picture by user ID - equivalent to Java UpdatePicByUserId method.
        Java: public ResponseEntity<String> UpdatePicByUserId(...)
        """
        try:
            fileURL = await self.addOrUpdateProfilePic(tenantId, profilePicDTO, file, isUpdate=True)
            return f"Profile picture updated successfully: {fileURL}"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to update profile picture: {str(e)}")

    async def setPassword(self, tenantId: str, passwordDTO: UpdatePasswordDTO) -> str:
        """
        Set password - equivalent to Java setPassword method.
        Java: public ResponseEntity<?> setPassword(@RequestHeader(value ="X-tenantID") String tenantId, @RequestBody UpdatePasswordDTO passwordDTO)
        """
        try:
            await self.updatePasswordByUUID(tenantId, passwordDTO)
            return "Password updated successfully"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to set password: {str(e)}")

    async def setSsoId(self, userSsoIdDTO: UserSsoIdDTO) -> str:
        """
        Set SSO ID - equivalent to Java setSsoId method.
        Java: public ResponseEntity<?> setSsoId(@RequestBody UserSsoIdDTO userSsoIdDTO)
        """
        try:
            await self.updateUserSsoIdByUUID(userSsoIdDTO)
            return "SSO ID updated successfully"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to set SSO ID: {str(e)}")

    # getMySurrogate method is implemented above at line 1777 with proper business logic

    # (Removed broken self-recursive alias methods that shadowed real implementations)

    async def blockOrDeactivateUser(
        self, 
        authorization: str,
        tenantId: str,
        userId: str, 
        option: BlockOrDeactivateAction
    ) -> str:
        """
        Block or deactivate user - matches Java signature exactly.
        Java: public ResponseEntity<String> blockOrDeactivateUser(@RequestHeader(value = "X-Authorization") String authorization, @RequestHeader(value = "X-tenantID") String tenantId,@PathVariable("id") String userId, @PathVariable("action") BlockOrDeactivateAction option)
        """
        try:
            user = await self.getUserById(userId, tenantId)
            
            if user is not None:
                if option == BlockOrDeactivateAction.BLOCK:
                    user.isBlocked = True
                    user.userBlockedOrDeactivatedDate = datetime.now()
                elif option == BlockOrDeactivateAction.DEACTIVATE:
                    user.isActivated = False
                    user.userBlockedOrDeactivatedDate = datetime.now()
                    
                    if authorization is not None:
                        userName = await self.extractUserNameFromOauthJwtToken(authorization, {})
                        actionBy = ActionBy(actionByUserId=userName, actionDateTime=datetime.now())
                        user.deactivatedBy = actionBy
                        
                elif option == BlockOrDeactivateAction.UNBLOCK:
                    user.isBlocked = False
                    user.userBlockedOrDeactivatedDate = None
                elif option == BlockOrDeactivateAction.REACTIVATE:
                    user.isActivated = True
                    user.isInvited = False
                    user.userBlockedOrDeactivatedDate = None
                elif option == BlockOrDeactivateAction.DELETE:
                    user.isDeleted = True
                
                # Persist changes
                await self.userRepository.save(user)
                # Return Java-like simple string response
                if option == BlockOrDeactivateAction.BLOCK:
                    return "User blocked successfully"
                if option == BlockOrDeactivateAction.UNBLOCK:
                    return "User unblocked successfully"
                if option == BlockOrDeactivateAction.DEACTIVATE:
                    return "User deactivated successfully"
                if option == BlockOrDeactivateAction.REACTIVATE:
                    return "User reactivated successfully"
                if option == BlockOrDeactivateAction.DELETE:
                    return "User deleted successfully"
                # Fallback (should not hit)
                return f"{option.value} action completed successfully"
            else:
                raise HTTPException(status_code=404, detail=f"User {userId} is not available in tenant: {tenantId}")
                
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=400, detail=f"Failed to {option.value} user: {str(e)}")

    async def changePassword(self, authorization: str, passwordDTO: ChangePasswordDTO) -> str:
        """
        Change password - matches Java signature exactly.
        Java: public ResponseEntity<?> changePassword(@RequestHeader(value = "X-Authorization") String authorization, @RequestBody ChangePasswordDTO passwordDTO)
        """
        try:
            # Extract user ID from authorization token (synchronous)
            userId = self.jwtUtil.getUserIdFromToken(authorization)
            
            await self.newPasswordValidation(userId, passwordDTO.newPassword)
            userPasswordDTO = UserPasswordDTO(
                userId=userId,
                password=passwordDTO.newPassword
            )
            
            user = await self.userRepository.findById(userId)
            tenantId = user.tenant.tenantId
            # Persist password change (this computes the bcrypt hash internally)
            saved_user = await self.setUserPassword(tenantId, userPasswordDTO)
            # Mirror the exact hash used to root field for visibility/back-compat
            try:
                await self.userRepository.updateById(
                    saved_user.id,
                    {
                        "password": {"encryptedPassword": saved_user.password.password if saved_user and saved_user.password else None},
                        "encryptedPassword": saved_user.password.password if saved_user and saved_user.password else None,
                        "isActivated": True,
                    },
                )
            except Exception:
                pass
            
            return "Password changed successfully"
            
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=400, detail=f"Failed to change password: {str(e)}")

    # ===== ADDITIONAL MISSING METHODS FROM JAVA =====

    async def forgetPassword(self, email: Email) -> str:
        """
        Forget password - equivalent to Java forgetPassword method.
        Java: public ResponseEntity<?> forgetPassword(@RequestBody Email email)
        """
        try:
            activationURL = await self.forgotPassword(email)
            return f"Password reset link sent successfully: {activationURL}"
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=400, detail=f"Failed to process forgot password: {str(e)}")

    async def patchUserByScimId(self, userId: str, patchRequest: Any) -> Any:
        """
        Patch user by SCIM ID using PATCH operations.
        Equivalent to Java patch operations for SCIM users.
        """
        from app.models.scim.ScimModels import ScimUser
        
        # Get existing user
        user = await self.getUserForScimById(userId)
        if not user:
            raise ValueError(f"User with id '{userId}' not found")
        
        # Apply patch operations
        for operation in patchRequest.Operations:
            op = operation.op.lower()
            path = operation.path
            value = operation.value
            
            if op == "replace":
                if path == "active":
                    user.active = value
                elif path == "userName":
                    user.userName = value
                elif path == "displayName":
                    user.displayName = value
                elif path == "name.givenName":
                    if not user.name:
                        from app.models.scim.ScimModels import ScimName
                        user.name = ScimName()
                    user.name.givenName = value
                elif path == "name.familyName":
                    if not user.name:
                        from app.models.scim.ScimModels import ScimName
                        user.name = ScimName()
                    user.name.familyName = value
                elif path == "emails":
                    user.emails = value
                elif path == "phoneNumbers":
                    user.phoneNumbers = value
                # Add more paths as needed
            
            elif op == "add":
                if path == "emails":
                    if not user.emails:
                        user.emails = []
                    if isinstance(value, list):
                        user.emails.extend(value)
                    else:
                        user.emails.append(value)
                # Add more paths as needed
            
            elif op == "remove":
                if path == "emails":
                    user.emails = []
                elif path and path.startswith("emails["):
                    # Remove specific email by filter
                    # This is simplified - in production use proper SCIM filter parsing
                    pass
                # Add more paths as needed
        
        # Update the user through regular update mechanism
        return await self.updateUserByScimResource(user)

    async def patchScimGroupById(self, groupId: str, patchRequest: Any) -> Any:
        """
        Patch SCIM group by ID using PATCH operations.
        Equivalent to Java patch operations for SCIM groups.
        """
        from app.models.scim.ScimModels import ScimGroup
        
        # Get existing group
        group = await self.getScimGroupById(groupId)
        if not group:
            raise ValueError(f"Group with id '{groupId}' not found")
        
        # Apply patch operations
        for operation in patchRequest.Operations:
            op = operation.op.lower()
            path = operation.path
            value = operation.value
            
            if op == "replace":
                if path == "displayName":
                    group.displayName = value
                elif path == "members":
                    group.members = value
                # Add more paths as needed
            
            elif op == "add":
                if path == "members":
                    if not group.members:
                        group.members = []
                    if isinstance(value, list):
                        group.members.extend(value)
                    else:
                        group.members.append(value)
                # Add more paths as needed
            
            elif op == "remove":
                if path == "members":
                    group.members = []
                elif path and path.startswith("members["):
                    # Remove specific member by filter
                    # This is simplified - in production use proper SCIM filter parsing
                    if group.members and value and 'value' in value:
                        group.members = [m for m in group.members if m.value != value['value']]
                # Add more paths as needed
        
        # Update the group through regular update mechanism
        return await self.updateScimGroup(group)

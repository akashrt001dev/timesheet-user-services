from pydantic import BaseModel, Field, field_validator
try:
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover
    ConfigDict = None  # type: ignore
from typing import Optional, List, Set
from datetime import datetime, timedelta
from ...entity.ProfilePicture import ProfilePicture
from ...entity.Role import Role
from ...valueobjects.AccessLevel import AccessLevel
from ...valueobjects.ActionBy import ActionBy
from ...valueobjects.Address import Address
from ...valueobjects.BillingInfo import BillingInfo
from ...valueobjects.Communication import Communication
from ...valueobjects.Contract import Contract
from ...valueobjects.ContractedServiceProviderType import ContractedServiceProviderType
from ...valueobjects.Email import Email
from ...valueobjects.LicenceDetails import LicenceDetails
from ...valueobjects.NPIN import NPIN
from ...valueobjects.Name import Name
from ...valueobjects.PartnerId import PartnerId
from ...valueobjects.Password import Password
from ...valueobjects.Sites import Sites
from ...valueobjects.SsoId import SsoId
from ...valueobjects.SurrogateSchedule import SurrogateSchedule
from ...valueobjects.Tenant import Tenant
from ...valueobjects.Title import Title
from ...valueobjects.UserType import UserType

class User(BaseModel):
    if ConfigDict:
        model_config = ConfigDict(populate_by_name=True)  # type: ignore
    id: Optional[str] = None
    name: Name
    userType: Optional[UserType] = None
    contracts: Optional[List[Contract]] = None
    title: Optional[Title] = None
    # Accept 'npin' from requests, keep internal 'nPIN'
    nPIN: Optional[NPIN] = Field(None, alias="npin")
    serviceProviderType: Optional[ContractedServiceProviderType] = None
    isActivated: bool = Field(False, alias="activated")
    isInvited: bool = Field(False, alias="invited")
    isPersonalEmailAddressAllowed: bool = Field(False, alias="personalEmailAddressAllowed")
    email: Optional[Email] = None
    password: Optional[Password] = None
    communication: Optional[Communication] = None
    roles: List[Role] = []  # Use List instead of Set to avoid hashable issues
    address: Optional[Address] = None
    tenant: Tenant
    sites: Optional[Sites] = None
    isExecutiveAccessLevelNeeded: bool = Field(False, alias="executiveAccessLevelNeeded")
    accessLevel: AccessLevel = AccessLevel.USER
    licenceDetails: Optional[LicenceDetails] = None
    isBlocked: bool = Field(False, alias="blocked")
    userCreatedDate: Optional[datetime] = None
    userBlockedOrDeactivatedDate: Optional[datetime] = None
    currentLogin: Optional[datetime] = None
    lastLogin: Optional[datetime] = None
    avgLoginCount: int = 0
    avgLoginSession: timedelta = timedelta(0)
    deactivatedBy: Optional[ActionBy] = None
    # Accept camelCase 'invitedBy'
    InvitedBy: Optional[ActionBy] = Field(None, alias="invitedBy")
    isDeleted: bool = Field(False, alias="deleted")
    loginAttempts: int = 0
    lockoutTime: int = 0
    passwordCreatedDate: Optional[datetime] = None
    profilePic: Optional[ProfilePicture] = None
    partnerId: Optional[PartnerId] = None
    ssoId: Optional[SsoId] = None
    professionalServicesBilling: Optional[BillingInfo] = None
    isSurrogateEnabled: bool = Field(False, alias="surrogateEnabled")
    surrogateSchedule: List[SurrogateSchedule] = []
    lastModifiedDate: Optional[datetime] = None
    externalId: Optional[str] = None

    # For Pydantic v1, provide Config; for v2, we already set model_config above
    if not ConfigDict:
        class Config:
            allow_population_by_field_name = True  # pydantic v1 key

    @field_validator('avgLoginSession', mode='before')
    @classmethod
    def parse_avg_login_session(cls, v):
        if v is None:
            return timedelta(0)
        if isinstance(v, dict) and 'millis' in v:
            # Convert millis to timedelta
            return timedelta(milliseconds=v['millis'])
        if isinstance(v, timedelta):
            return v
        return timedelta(0)
    
    @field_validator('password', mode='before')
    @classmethod
    def parse_password(cls, v):
        if isinstance(v, dict):
            # Handle MongoDB password structure
            if 'encryptedPassword' in v:
                return {'password': v['encryptedPassword']}
            elif 'password' in v:
                return {'password': v['password']}
        return v

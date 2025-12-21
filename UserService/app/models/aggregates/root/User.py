from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, timedelta

from ...entity.ProfilePicture import ProfilePicture
from ...entity.Role import Role
from ...valueobjects.AccessLevel import AccessLevel
from ...valueobjects.AccessScope import AccessScope
from ...valueobjects.ActionBy import ActionBy
from ...valueobjects.Address import Address
from ...valueobjects.BillingInfo import BillingInfo
from ...valueobjects.Communication import Communication
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
    id: Optional[str] = Field(None, alias="_id", serialization_alias="id")

    # Required fields (as per Spring Boot @NotNull)
    name: Name
    email: Email
    communication: Communication
    tenant: Tenant

    # Optional fields
    userType: Optional[UserType] = None
    title: Optional[Title] = None
    nPIN: Optional[NPIN] = Field(None, alias="npin")
    serviceProviderType: Optional[ContractedServiceProviderType] = None

    isActivated: bool = Field(False, alias="activated")
    isInvited: bool = Field(False, alias="invited")
    isPersonalEmailAddressAllowed: bool = Field(False, alias="personalEmailAddressAllowed")

    password: Optional[Password] = None  # Optional for update
    roles: List[Role] = []
    accessScope: Optional[AccessScope] = None
    address: Optional[Address] = None

    sites: Optional[Sites] = None  # Temporary (as per Java comment)

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

    class Config:
        populate_by_name = True  # Allow both alias (_id) and field name (id) when parsing
        # Note: Pydantic v2 uses populate_by_name instead of allow_population_by_field_name

    # -------- Validators -------- #

    @field_validator("avgLoginSession", mode="before")
    @classmethod
    def parse_avg_login_session(cls, v):
        if v is None:
            return timedelta(0)
        if isinstance(v, dict) and "millis" in v:
            return timedelta(milliseconds=v["millis"])
        if isinstance(v, timedelta):
            return v
        return timedelta(0)

    @field_validator("password", mode="before")
    @classmethod
    def parse_password(cls, v):
        if isinstance(v, dict):
            if "encryptedPassword" in v:
                return {"password": v["encryptedPassword"]}
            if "password" in v:
                return {"password": v["password"]}
        return v

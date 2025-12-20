from pydantic import BaseModel, Field
try:
    # Pydantic v2
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover
    ConfigDict = None  # type: ignore
from typing import List, Set, Optional
from datetime import datetime


from ..aggregates.root.User import User
from ..entity.ProfilePicture import ProfilePicture
from ..entity.Role import Role
from ..valueobjects.AccessLevel import AccessLevel
from ..valueobjects.ActionBy import ActionBy
from ..valueobjects.Address import Address
from ..valueobjects.BillingInfo import BillingInfo
from ..valueobjects.Communication import Communication
from ..valueobjects.Contract import Contract
from ..valueobjects.ContractedServiceProviderType import ContractedServiceProviderType
from ..valueobjects.LicenceDetails import LicenceDetails
from ..valueobjects.NPIN import NPIN
from ..valueobjects.Name import Name
from ..valueobjects.Email import Email
from ..valueobjects.PartnerId import PartnerId
from ..valueobjects.Password import Password
from ..valueobjects.Sites import Sites
from ..valueobjects.SsoId import SsoId
from ..valueobjects.SurrogateSchedule import SurrogateSchedule
from ..valueobjects.Tenant import Tenant
from ..valueobjects.Title import Title
from ..valueobjects.UserType import UserType
from .AccessScopeResponseDTO import AccessScopeResponseDTO

class UserDTO(BaseModel):
    # Accept both field names and aliases across pydantic versions
    if ConfigDict:
        model_config = ConfigDict(populate_by_name=True)  # type: ignore
    else:
        class Config:
            allow_population_by_field_name = True

    id: Optional[str] = None
    name: Optional['Name'] = None
    userType: Optional['UserType'] = None
    contracts: Optional[List['Contract']] = []
    title: Optional['Title'] = None
    email: Optional['Email'] = None
    password: Optional['Password'] = None
    communication: Optional['Communication'] = None
    roles: List['Role'] = Field(default_factory=list)
    address: Optional['Address'] = None
    tenant: Optional['Tenant'] = None
    partnerId: Optional['PartnerId'] = None
    sites: Optional['Sites'] = None
    accessScope: Optional['AccessScopeResponseDTO'] = None
    # Accept lowercase 'npin' from requests, map to internal nPIN
    nPIN: Optional['NPIN'] = Field(None, alias="npin")
    serviceProviderType: Optional['ContractedServiceProviderType'] = None
    isExecutiveAccessLevelNeeded: bool = Field(False, alias="executiveAccessLevelNeeded")
    accessLevel: Optional['AccessLevel'] = None
    isSiteLevelResponsible: bool = Field(False, alias="siteLevelResponsible")
    isDepartmentLevelResponsible: bool = Field(False, alias="departmentLevelResponsible")
    isActivated: bool = Field(False, alias="activated")
    isInvited: bool = Field(False, alias="invited")
    isPersonalEmailAddressAllowed: bool = Field(False, alias="personalEmailAddressAllowed")
    isDeleted: bool = Field(False, alias="deleted")
    licenceDetails: Optional['LicenceDetails'] = None
    isBlocked: bool = Field(False, alias="blocked")
    userCreatedDate: Optional[datetime] = None
    userBlockedOrDeactivatedDate: Optional[datetime] = None
    currentLogin: Optional[datetime] = None
    lastLogin: Optional[datetime] = None
    avgLoginCount: int = 0
    deactivatedBy: Optional['ActionBy'] = None
    # Accept camelCase 'invitedBy' from requests
    InvitedBy: Optional['ActionBy'] = Field(None, alias="invitedBy")
    passwordCreatedDate: Optional[datetime] = None
    profilePic: Optional['ProfilePicture'] = None
    ssoId: Optional['SsoId'] = None
    professionalServicesBilling: Optional['BillingInfo'] = None
    isSurrogateEnabled: bool = Field(False, alias="surrogateEnabled")
    surrogateSchedule: Optional[List['SurrogateSchedule']] = []

    def to_domain(self) -> 'User':
        """Convert DTO to domain User model.
        Only includes fields that are explicitly provided (not None).
        Supports partial updates by skipping None values.
        """
        from ..aggregates.root.User import User
        from ..valueobjects.AccessScope import AccessScope, Role, Region
        
        payload = {}
        
        # Only include fields that are explicitly provided
        if self.id is not None:
            payload['id'] = self.id
        if self.name is not None:
            payload['name'] = self.name
        if self.email is not None:
            payload['email'] = self.email
        if self.password is not None:
            payload['password'] = self.password
        if self.communication is not None:
            payload['communication'] = self.communication
        if self.tenant is not None:
            payload['tenant'] = self.tenant
        if self.userType is not None:
            payload['userType'] = self.userType
        if self.contracts is not None and len(self.contracts) > 0:
            payload['contracts'] = self.contracts
        if self.title is not None:
            payload['title'] = self.title
        if self.roles is not None and len(self.roles) > 0:
            payload['roles'] = list(self.roles)
        if self.address is not None:
            payload['address'] = self.address
        if self.partnerId is not None:
            payload['partnerId'] = self.partnerId
        if self.sites is not None:
            payload['sites'] = self.sites
        
        # Convert AccessScopeResponseDTO to AccessScope domain model
        if self.accessScope is not None:
            try:
                # AccessScopeResponseDTO has structure: roles[] and accessScopes[]
                # Convert to domain AccessScope structure: roles[] and regions[]
                access_scope_data = {}
                
                # Extract roles from the response DTO
                if self.accessScope.roles:
                    access_scope_data['roles'] = [
                        Role(
                            id=role.id,
                            roleName=role.roleName,
                            roleDescription=role.roleDescription,
                            roleType=role.roleType,
                            rolePerformerTypes=role.rolePerformerTypes or []
                        )
                        for role in self.accessScope.roles
                    ]
                else:
                    access_scope_data['roles'] = []
                
                # Extract regions from accessScopes
                regions = []
                if self.accessScope.accessScopes:
                    # Each AccessScopeDetailDTO can have regions
                    for scope_detail in self.accessScope.accessScopes:
                        if scope_detail.regions:
                            # Convert RegionDTO to Region domain model
                            for region_dto in scope_detail.regions:
                                try:
                                    # Handle RegionDTO structure - convert to dict for Region model
                                    region_dict = region_dto.model_dump() if hasattr(region_dto, 'model_dump') else region_dto.__dict__
                                    region = Region(**region_dict)
                                    regions.append(region)
                                except Exception as region_e:
                                    print(f"Warning: Could not convert region: {region_e}")
                                    continue
                
                access_scope_data['regions'] = regions or []
                access_scope_data['allRegionsApplicable'] = False
                
                payload['accessScope'] = AccessScope(**access_scope_data)
                print(f"[to_domain] Successfully converted accessScope with {len(regions)} regions")
            except Exception as e:
                # If conversion fails, log and skip accessScope
                print(f"Warning: Could not convert accessScope: {e}")
                import traceback
                traceback.print_exc()
                pass
        
        if self.nPIN is not None:
            payload['nPIN'] = self.nPIN
        if self.serviceProviderType is not None:
            payload['serviceProviderType'] = self.serviceProviderType
        if self.accessLevel is not None:
            payload['accessLevel'] = self.accessLevel
        if self.licenceDetails is not None:
            payload['licenceDetails'] = self.licenceDetails
        if self.userCreatedDate is not None:
            payload['userCreatedDate'] = self.userCreatedDate
        if self.userBlockedOrDeactivatedDate is not None:
            payload['userBlockedOrDeactivatedDate'] = self.userBlockedOrDeactivatedDate
        if self.currentLogin is not None:
            payload['currentLogin'] = self.currentLogin
        if self.lastLogin is not None:
            payload['lastLogin'] = self.lastLogin
        if self.avgLoginCount is not None and self.avgLoginCount > 0:
            payload['avgLoginCount'] = self.avgLoginCount
        if self.deactivatedBy is not None:
            payload['deactivatedBy'] = self.deactivatedBy
        if self.InvitedBy is not None:
            payload['InvitedBy'] = self.InvitedBy
        if self.passwordCreatedDate is not None:
            payload['passwordCreatedDate'] = self.passwordCreatedDate
        if self.profilePic is not None:
            payload['profilePic'] = self.profilePic
        if self.ssoId is not None:
            payload['ssoId'] = self.ssoId
        if self.professionalServicesBilling is not None:
            payload['professionalServicesBilling'] = self.professionalServicesBilling
        if self.surrogateSchedule is not None and len(self.surrogateSchedule) > 0:
            payload['surrogateSchedule'] = self.surrogateSchedule
        
        # Include all boolean flags (they have defaults)
        payload['isExecutiveAccessLevelNeeded'] = bool(self.isExecutiveAccessLevelNeeded)
        payload['isSiteLevelResponsible'] = bool(self.isSiteLevelResponsible)
        payload['isDepartmentLevelResponsible'] = bool(self.isDepartmentLevelResponsible)
        payload['isActivated'] = bool(self.isActivated)
        payload['isInvited'] = bool(self.isInvited)
        payload['isPersonalEmailAddressAllowed'] = bool(self.isPersonalEmailAddressAllowed)
        payload['isDeleted'] = bool(self.isDeleted)
        payload['isBlocked'] = bool(self.isBlocked)
        payload['isSurrogateEnabled'] = bool(self.isSurrogateEnabled)
        
        return User(**payload)
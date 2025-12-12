from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class ScimMeta(BaseModel):
    """
    SCIM Meta object containing metadata about a resource
    """
    resourceType: str
    created: Optional[datetime] = None
    lastModified: Optional[datetime] = None
    location: Optional[str] = None
    version: Optional[str] = None

class ScimName(BaseModel):
    """
    SCIM Name object for user names
    """
    formatted: Optional[str] = None
    familyName: Optional[str] = None
    givenName: Optional[str] = None
    middleName: Optional[str] = None
    honorificPrefix: Optional[str] = None
    honorificSuffix: Optional[str] = None

class ScimEmail(BaseModel):
    """
    SCIM Email object
    """
    value: str
    type: Optional[str] = "work"
    primary: Optional[bool] = True

class ScimPhoneNumber(BaseModel):
    """
    SCIM Phone Number object
    """
    value: str
    type: Optional[str] = "work"
    primary: Optional[bool] = True

class ScimAddress(BaseModel):
    """
    SCIM Address object
    """
    formatted: Optional[str] = None
    streetAddress: Optional[str] = None
    locality: Optional[str] = None
    region: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None
    type: Optional[str] = "work"
    primary: Optional[bool] = True

class ScimPhoto(BaseModel):
    """
    SCIM Photo object
    """
    value: str
    type: Optional[str] = "photo"

class ScimEntitlement(BaseModel):
    """
    SCIM Entitlement object
    """
    value: str
    display: Optional[str] = None
    type: Optional[str] = None
    primary: Optional[bool] = False

class ScimRole(BaseModel):
    """
    SCIM Role object
    """
    value: str
    display: Optional[str] = None
    type: Optional[str] = None
    primary: Optional[bool] = False

class ScimX509Certificate(BaseModel):
    """
    SCIM X509 Certificate object
    """
    value: str
    display: Optional[str] = None
    type: Optional[str] = None
    primary: Optional[bool] = False

class ScimUser(BaseModel):
    """
    SCIM User resource as defined in RFC 7643
    """
    schemas: List[str] = Field(default=["urn:ietf:params:scim:schemas:core:2.0:User"])
    id: Optional[str] = None
    externalId: Optional[str] = None
    meta: Optional[ScimMeta] = None
    userName: str
    name: Optional[ScimName] = None
    displayName: Optional[str] = None
    nickName: Optional[str] = None
    profileUrl: Optional[str] = None
    title: Optional[str] = None
    userType: Optional[str] = None
    preferredLanguage: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    active: Optional[bool] = True
    password: Optional[str] = None
    emails: Optional[List[ScimEmail]] = None
    phoneNumbers: Optional[List[ScimPhoneNumber]] = None
    ims: Optional[List[Dict[str, Any]]] = None
    photos: Optional[List[ScimPhoto]] = None
    addresses: Optional[List[ScimAddress]] = None
    groups: Optional[List[Dict[str, str]]] = None
    entitlements: Optional[List[ScimEntitlement]] = None
    roles: Optional[List[ScimRole]] = None
    x509Certificates: Optional[List[ScimX509Certificate]] = None

class ScimGroupMember(BaseModel):
    """
    SCIM Group Member object
    """
    value: str
    ref: Optional[str] = Field(alias="$ref", default=None)
    display: Optional[str] = None
    type: Optional[str] = "User"

class ScimGroup(BaseModel):
    """
    SCIM Group resource as defined in RFC 7643
    """
    schemas: List[str] = Field(default=["urn:ietf:params:scim:schemas:core:2.0:Group"])
    id: Optional[str] = None
    externalId: Optional[str] = None
    meta: Optional[ScimMeta] = None
    displayName: str
    members: Optional[List[ScimGroupMember]] = None

class ScimError(BaseModel):
    """
    SCIM Error response as defined in RFC 7644
    """
    schemas: List[str] = Field(default=["urn:ietf:params:scim:api:messages:2.0:Error"])
    detail: Optional[str] = None
    status: str
    scimType: Optional[str] = None

class ScimListResponse(BaseModel):
    """
    SCIM List Response as defined in RFC 7644
    """
    schemas: List[str] = Field(default=["urn:ietf:params:scim:api:messages:2.0:ListResponse"])
    totalResults: int
    startIndex: Optional[int] = 1
    itemsPerPage: Optional[int] = None
    Resources: List[Any]

class ScimPartialListResponse(BaseModel):
    """
    SCIM Partial List Response for pagination
    """
    schemas: List[str] = Field(default=["urn:ietf:params:scim:api:messages:2.0:ListResponse"])
    totalResults: int
    startIndex: int
    itemsPerPage: int
    Resources: List[Any]

class ScimPatchOperation(BaseModel):
    """
    SCIM Patch Operation as defined in RFC 7644
    """
    op: str  # "add", "remove", "replace"
    path: Optional[str] = None
    value: Optional[Any] = None

class ScimPatchRequest(BaseModel):
    """
    SCIM Patch Request as defined in RFC 7644
    """
    schemas: List[str] = Field(default=["urn:ietf:params:scim:api:messages:2.0:PatchOp"])
    Operations: List[ScimPatchOperation]

class ScimBulkRequest(BaseModel):
    """
    SCIM Bulk Request as defined in RFC 7644
    """
    schemas: List[str] = Field(default=["urn:ietf:params:scim:api:messages:2.0:BulkRequest"])
    failOnErrors: Optional[int] = None
    Operations: List[Dict[str, Any]]

class ScimBulkResponse(BaseModel):
    """
    SCIM Bulk Response as defined in RFC 7644
    """
    schemas: List[str] = Field(default=["urn:ietf:params:scim:api:messages:2.0:BulkResponse"])
    Operations: List[Dict[str, Any]]

class ScimResourceType(BaseModel):
    """
    SCIM Resource Type as defined in RFC 7643
    """
    schemas: List[str] = Field(default=["urn:ietf:params:scim:schemas:core:2.0:ResourceType"])
    id: str
    name: str
    endpoint: str
    description: Optional[str] = None
    schema_: str = Field(alias="schema")
    schemaExtensions: Optional[List[Dict[str, Any]]] = None
    meta: Optional[ScimMeta] = None

class ScimServiceProviderConfig(BaseModel):
    """
    SCIM Service Provider Configuration as defined in RFC 7643
    """
    schemas: List[str] = Field(default=["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"])
    documentationUri: Optional[str] = None
    patch: Dict[str, bool] = Field(default={"supported": True})
    bulk: Dict[str, Any] = Field(default={"supported": True, "maxOperations": 1000, "maxPayloadSize": 1048576})
    filter: Dict[str, Any] = Field(default={"supported": True, "maxResults": 200})
    changePassword: Dict[str, bool] = Field(default={"supported": True})
    sort: Dict[str, bool] = Field(default={"supported": True})
    etag: Dict[str, bool] = Field(default={"supported": False})
    authenticationSchemes: List[Dict[str, Any]] = Field(default=[
        {
            "type": "httpbearer",
            "name": "Bearer Token",
            "description": "Authentication scheme using Bearer Token",
            "specUri": "http://www.rfc-editor.org/info/rfc6750",
            "documentationUri": "https://tools.ietf.org/html/rfc6750"
        }
    ])
    meta: Optional[ScimMeta] = None

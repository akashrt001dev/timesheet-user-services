from pydantic import BaseModel, Field
from typing import Optional
from app.models.valueobjects.ContractLite import ContractLite
from app.models.valueobjects.ContractName import ContractName
from app.models.valueobjects.ContractStatus import ContractStatus
from app.models.valueobjects.EntityId import EntityId
from app.models.valueobjects.ContractDetail import ContractDetail


class UserClientDTO(BaseModel):
    """
    User Client Data Transfer Object - Primary request body for /contract/updateStatus endpoint.
    
    Equivalent to Java: ContractLite model with comprehensive field definitions.
    
    This DTO represents the contract update request that triggers the user onboarding
    email workflow. It contains all contract information needed to identify which users
    should receive welcome emails and determine the email content type.
    
    Field Mapping (Java → Python):
    - id: String → str (Contract identifier, used to query uninvited users)
    - contractName: ContractName → ContractName valueobject
    - contractStatus: ContractStatus → ContractStatus enum (ACTIVE or ACTIVATION_READY triggers emails)
    - tenant: EntityId → EntityId valueobject (tenant/organization reference)
    - contractDetail: ContractDetail → ContractDetail valueobject (contract terms and dates)
    
    Status Logic:
    - ACTIVE: Generate domain login URL (https://{subdomain}.timesmart.ai)
    - ACTIVATION_READY: Generate SSO URL with token
    - Other (DRAFT, EXPIRED, TERMINATED): Skip email sending
    """
    
    id: Optional[str] = Field(
        None,
        description="Contract identifier used to query uninvited users from database"
    )
    
    contractName: Optional[ContractName] = Field(
        None,
        description="Contract name valueobject containing organization contract name"
    )
    
    contractStatus: Optional[ContractStatus] = Field(
        None,
        description="Contract status enum that controls email sending logic. Only ACTIVE and ACTIVATION_READY trigger emails."
    )
    
    tenant: Optional[EntityId] = Field(
        None,
        description="Entity/Tenant reference used to fetch organization details and route emails"
    )
    
    contractDetail: Optional[ContractDetail] = Field(
        None,
        description="Contract detail containing contract terms with start/end dates and activation date"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "user-client-001",
                "contractName": {
                    "contractName": "Enterprise Contract"
                },
                "contractStatus": "ACTIVE",
                "tenant": {
                    "id": "tenant-123"
                },
                "contractDetail": {
                    "contractTerm": {
                        "startDate": "2024-01-01",
                        "endDate": "2024-12-31",
                        "effectiveDate": "2024-01-01",
                        "activationDate": "2024-01-05"
                    }
                }
            }
        }

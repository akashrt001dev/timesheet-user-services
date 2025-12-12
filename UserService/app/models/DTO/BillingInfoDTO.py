from pydantic import BaseModel, EmailStr
from typing import Optional


from ..valueobjects.BillingInfo import BillingInfo

class BillingInfoDTO(BaseModel):
    name: Optional[str]
    email: Optional[EmailStr] # Assuming Email value object maps to EmailStr
    mobileNumber: Optional[str]

    def to_domain(self) -> 'BillingInfo':
        from ..valueobjects.BillingInfo import BillingInfo
        return BillingInfo(**self.dict())
from pydantic import BaseModel
from typing import Optional
from .Email import Email

class BillingInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[Email] = None
    mobileNumber: Optional[str] = None

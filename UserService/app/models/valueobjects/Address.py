from pydantic import BaseModel
from typing import Optional

class Address(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None
    addressLine: Optional[str] = None

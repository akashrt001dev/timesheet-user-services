from pydantic import BaseModel, EmailStr, Field
from typing import List, Dict, Any, Optional

class EmailDTO(BaseModel):
    templateName: Optional[str]
    from_email: Optional[EmailStr] = Field(None, alias="from")
    to: Optional[List[EmailStr]] = []
    subject: Optional[str]
    cc: Optional[List[EmailStr]] = []
    bcc: Optional[List[EmailStr]] = []
    tenantId: Optional[str]
    templateValue: Optional[Dict[str, Any]] = {}

    class Config:
        allow_population_by_field_name = True
from pydantic import BaseModel, Field
try:
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover
    ConfigDict = None  # type: ignore
from typing import Optional

class Communication(BaseModel):
    if ConfigDict:
        model_config = ConfigDict(populate_by_name=True)  # type: ignore
    else:
        class Config:
            allow_population_by_field_name = True
    personalEmail: Optional[str] = None  # Make optional since it's missing from MongoDB docs
    mobileNumber: Optional[str] = Field(None, alias="phoneNumber")  # Map to phoneNumber field
    landlineNumber: Optional[str] = Field(None, alias="alternatePhoneNumber")
    faxNumber: Optional[str] = None
    isMobileNumberNotApplicable: bool = Field(False, alias="mobileNumberNotApplicable")

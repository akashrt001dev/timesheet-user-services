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
    personalEmail: Optional[str] = None
    mobileNumber: Optional[str] = None
    landlineNumber: Optional[str] = None
    faxNumber: Optional[str] = None
    isMobileNumberNotApplicable: bool = Field(False, alias="mobileNumberNotApplicable")

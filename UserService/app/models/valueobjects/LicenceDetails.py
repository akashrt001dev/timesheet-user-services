from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class LicenceDetails(BaseModel):
    medicalLicense: Optional[str] = None
    licenseExpiryDate: Optional[date] = None
    deaNumber: Optional[str] = None
    deaExpiryDate: Optional[date] = None
    boardCertification: Optional[List[str]] = None

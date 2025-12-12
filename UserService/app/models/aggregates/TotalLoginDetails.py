from pydantic import BaseModel
from typing import Dict
from datetime import date
from ..valueobjects.LoginDetails import LoginDetails

class TotalLoginDetails(BaseModel):
    loginDetails: Dict[date, LoginDetails] = {}

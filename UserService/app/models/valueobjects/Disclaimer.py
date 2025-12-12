from pydantic import BaseModel
from typing import Optional

class Disclaimer(BaseModel):
    paymentNote: Optional[str] = None

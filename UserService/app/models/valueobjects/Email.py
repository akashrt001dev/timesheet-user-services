from pydantic import BaseModel
from typing import Optional

class Email(BaseModel):
    officialEmail: Optional[str] = ""

from pydantic import BaseModel, EmailStr
from typing import Optional

class AuthRequest(BaseModel):
    email: Optional[EmailStr]
    password: Optional[str]
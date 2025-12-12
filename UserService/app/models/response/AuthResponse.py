from pydantic import BaseModel
from typing import Optional

class AuthResponse(BaseModel):
    accessToken: Optional[str]
    refreshToken: Optional[str]
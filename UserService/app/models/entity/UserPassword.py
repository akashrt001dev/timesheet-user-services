from pydantic import BaseModel
from typing import Optional, List

class UserPassword(BaseModel):
    id: Optional[str] = None
    userId: Optional[str] = None
    # Stores the last N encoded password hashes (strings), newest at the end
    passwordList: Optional[List[str]] = None

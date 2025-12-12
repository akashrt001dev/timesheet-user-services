from pydantic import BaseModel

class UserAvgLoginSession(BaseModel):
    avgLogin: int

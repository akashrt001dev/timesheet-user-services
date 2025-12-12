from pydantic import BaseModel

class UserAvgLoginCount(BaseModel):
    avgCount: int

from pydantic import BaseModel
from typing import List
from .SurrogateUser import SurrogateUser

class MySurrogate(BaseModel):
    proxyIdList: List[SurrogateUser] = []

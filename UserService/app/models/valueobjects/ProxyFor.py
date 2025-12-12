from pydantic import BaseModel
from typing import List
from .SurrogateUser import SurrogateUser

class ProxyFor(BaseModel):
    proxyIdList: List[SurrogateUser] = []

from pydantic import BaseModel
from typing import Optional, List
from .SurrogateJobDetails import SurrogateJobDetails

class UserJobDetails(BaseModel):
    id: Optional[str] = None
    surrogateJobDetails: Optional[List[SurrogateJobDetails]] = None

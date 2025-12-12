from pydantic import BaseModel
from typing import Optional, Any
from .Name import Name
from .Title import Title

class SurrogateUser(BaseModel):
    id: Optional[str] = None
    name: Optional[Name] = None
    title: Optional[Title] = None

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, SurrogateUser):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

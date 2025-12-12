from pydantic import BaseModel, Field
from typing import Optional

class Member(BaseModel):
    type: Optional[str] = None
    primary: Optional[bool] = None
    display: Optional[str] = None
    value: Optional[str] = None
    ref: Optional[str] = Field(None, alias="ref")

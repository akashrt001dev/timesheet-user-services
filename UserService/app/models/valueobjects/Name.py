from pydantic import BaseModel, field_validator
from typing import Optional, Union
from .Suffix import Suffix

class Name(BaseModel):
    firstName: Optional[str] = ""
    lastName: Optional[str] = ""
    middleName: str = ""
    suffix: Optional[Suffix] = None

    @field_validator('suffix', mode='before')
    @classmethod
    def parse_suffix(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            # If suffix is a string, convert it to Suffix object
            return Suffix(suffix=v)
        if isinstance(v, dict) and not v:
            # If suffix is empty dict, return None
            return None
        return v

    @property
    def fullName(self) -> str:
        if self.middleName:
            return f"{self.firstName} {self.middleName} {self.lastName}"
        return f"{self.firstName} {self.lastName}"

    def getFullName(self) -> str:
        """Backward compatibility method. Use fullName property instead."""
        return self.fullName

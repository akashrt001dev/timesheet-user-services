from pydantic import BaseModel, field_validator
from typing import Optional

class SsoId(BaseModel):
    id: Optional[str] = None

    @field_validator('id', mode='before')
    @classmethod
    def parse_id_from_mongodb(cls, v):
        """
        Handle MongoDB's _id field in nested objects.
        MongoDB stores as { _id: "value" }, but Pydantic expects { id: "value" }
        This validator accepts both formats.
        """
        if isinstance(v, dict):
            # If passed a dict, extract the 'id' or '_id' field
            return v.get('id') or v.get('_id')
        # If passed a string, return as-is
        return v

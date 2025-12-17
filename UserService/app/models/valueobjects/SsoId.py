from pydantic import BaseModel, field_validator
from typing import Optional

class SsoId(BaseModel):
    id: Optional[str] = None

    @field_validator('id', mode='before')
    @classmethod
    def parse_id_from_mongodb(cls, v):
        """
        Handle MongoDB's _id field and ObjectId conversions.
        MongoDB stores as { _id: "value" } or { _id: ObjectId(...) }, but Pydantic expects { id: "value" }
        This validator accepts all formats and converts ObjectId to string.
        """
        if v is None:
            return None
        # Handle ObjectId
        if hasattr(v, '__str__') and type(v).__name__ == 'ObjectId':
            return str(v)
        # If passed a dict, extract the 'id' or '_id' field
        if isinstance(v, dict):
            return v.get('id') or v.get('_id')
        # Already a string
        return str(v) if v else None

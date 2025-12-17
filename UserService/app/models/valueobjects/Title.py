from pydantic import BaseModel, field_validator
from typing import Optional

class Title(BaseModel):
    title: Optional[str] = None
    id: Optional[str] = None

    @field_validator('id', mode='before')
    @classmethod
    def convert_object_id_to_string(cls, v):
        """
        Convert MongoDB ObjectId to string.
        MongoDB stores IDs as ObjectId objects, but Pydantic expects strings.
        """
        if v is None:
            return None
        # Handle ObjectId
        if hasattr(v, '__str__') and type(v).__name__ == 'ObjectId':
            return str(v)
        # Handle dict (nested _id field)
        if isinstance(v, dict):
            return v.get('id') or v.get('_id')
        # Already a string
        return str(v) if v else None

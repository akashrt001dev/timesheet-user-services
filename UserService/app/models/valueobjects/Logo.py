from pydantic import BaseModel
from typing import Optional
from ..reference_object.File import File

class Logo(BaseModel):
    file: Optional[File] = None

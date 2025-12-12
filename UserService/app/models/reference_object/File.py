from pydantic import BaseModel
from typing import Optional

class File(BaseModel):
    filePath: Optional[str] = None
    fileName: Optional[str] = None
    fileURL: Optional[str] = None

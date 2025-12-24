from pydantic import BaseModel, ConfigDict

class Tenant(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,  # Allow using both field name and alias
        str_strip_whitespace=True,  # Clean string data
    )
    
    tenantId: str

from pydantic import BaseModel

class Tenant(BaseModel):
    tenantId: str

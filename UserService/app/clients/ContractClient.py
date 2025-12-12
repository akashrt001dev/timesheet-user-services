import httpx
from typing import Any, Optional
from pydantic import BaseModel
from app.core.config import settings # Assuming settings are in core.config

# Placeholder for the actual Pydantic model you would use
class ContractStatus(BaseModel):
    # Define the fields for ContractStatus, e.g., status: str
    pass

class ContractClient:
    """
    Asynchronous client for interacting with the Contract Management Service.
    Migrated from the ContractClient.java Feign interface.
    """
    def __init__(self):
        self.base_url = settings.CONTRACT_CLIENT_URL
        self.client = httpx.AsyncClient(base_url=self.base_url)

    async def get_contract_status_by_id(self, contract_id: str) -> Optional[ContractStatus]:
        """
        Corresponds to: @GetMapping("contracts/{id}/status")
        """
        try:
            response = await self.client.get(f"/contracts/{contract_id}/status")
            response.raise_for_status()  # Raises an exception for 4xx/5xx responses
            return ContractStatus(**response.json())
        except httpx.HTTPStatusError as e:
            # Handle specific HTTP errors (e.g., 404 Not Found)
            print(f"HTTP error occurred: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None
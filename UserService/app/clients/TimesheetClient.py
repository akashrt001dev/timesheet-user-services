import httpx
from typing import Any, Optional
from app.core.config import settings

class TimesheetClient:
    """
    Asynchronous client for interacting with the Timesheet Service.
    Migrated from the TimesheetClient.java Feign interface.
    """
    def __init__(self):
        self.base_url = settings.TIMESHEET_CLIENT_URL
        self.client = httpx.AsyncClient(base_url=self.base_url)

    async def get_timesheet_data(self, contract_id: str, user_id: str, tenant_id: str) -> Optional[Any]:
        """
        Corresponds to: @GetMapping("/timesheet")
        Returns a generic object (dict or list in Python) as the original return type was Object.
        """
        headers = {"X-tenantID": tenant_id}
        params = {"contractIds": contract_id, "userId": user_id}
        try:
            response = await self.client.get("/timesheet", headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred while fetching timesheet data: {e}")
            return None
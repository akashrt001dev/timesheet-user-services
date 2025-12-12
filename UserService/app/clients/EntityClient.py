import httpx


from typing import List, Optional
from pydantic import BaseModel
from app.core.config import settings
from app.models.DTO.EntityDTO import EntityDTO
from app.models.aggregates.Site import Site
from app.models.valueobjects.Tenant import Tenant

class EntityClient:
    """
    Asynchronous client for interacting with the Entity Service.
    Migrated from the EntityClient.java Feign interface.
    """
    def __init__(self):
        self.base_url = settings.ENTITY_CLIENT_URL
        self.client = httpx.AsyncClient(base_url=self.base_url)

    async def get_entity_by_id(self, entity_id: str) -> Optional[EntityDTO]:
        """
        Corresponds to: @GetMapping("/entity/{id}")
        """
        try:
            response = await self.client.get(f"/entity/{entity_id}")
            response.raise_for_status()
            return EntityDTO(**response.json())
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred while fetching entity {entity_id}: {e}")
            return None

    async def get_all_sites_by_entity_id(self, tenant_id: str, site_name: str) -> List[Site]:
        """
        Corresponds to: @GetMapping("/sites")
        """
        headers = {"X-tenantID": tenant_id}
        params = {"siteName": site_name}
        try:
            response = await self.client.get("/sites", headers=headers, params=params)
            response.raise_for_status()
            return [Site(**item) for item in response.json()]
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred while fetching sites: {e}")
            return []

    async def get_entity_id_by_sub_domain(self, sub_domain: str) -> Optional[Tenant]:
        """
        Corresponds to: @GetMapping("/entityID/subDomain")
        """
        params = {"subDomain": sub_domain}
        try:
            response = await self.client.get("/entityID/subDomain", params=params)
            response.raise_for_status()
            return Tenant(**response.json())
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred while fetching entity by subdomain {sub_domain}: {e}")
            return None

    async def get_entity_by_realm(self, realm: str) -> Optional[EntityDTO]:
        """
        Get entity by realm/tenant identifier.
        Corresponds to: @GetMapping("/entity/realm/{realm}")
        """
        try:
            response = await self.client.get(f"/entity/realm/{realm}")
            response.raise_for_status()
            return EntityDTO(**response.json())
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred while fetching entity by realm {realm}: {e}")
            return None
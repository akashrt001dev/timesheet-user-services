from typing import Dict, Any, Optional, List
import json
import re
from urllib.parse import urlparse, parse_qs
from fastapi import HTTPException

from app.scim.ScimContext import ScimContext
from app.scim.ScimResponse import ScimResponse
from app.scim.UserHandler import UserHandler
from app.scim.GroupHandler import GroupHandler
from app.models.scim.ScimModels import (
    ScimUser, ScimGroup, ScimError, ScimListResponse,
    ScimResourceType, ScimServiceProviderConfig, ScimMeta
)

class ResourceEndpoint:
    """
    Python equivalent of de.captaingoldfish.scim.sdk.server.endpoints.ResourceEndpoint
    Main entry point for handling SCIM requests
    """
    
    def __init__(self, userHandler: UserHandler, groupHandler: GroupHandler):
        self.userHandler = userHandler
        self.groupHandler = groupHandler
        self.resourceTypes = self._initializeResourceTypes()
        self.serviceProviderConfig = self._initializeServiceProviderConfig()
    
    async def handleRequest(
        self,
        url: str,
        httpMethod: str,
        requestBody: Optional[str],
        httpHeaders: Dict[str, str],
        context: ScimContext
    ) -> ScimResponse:
        """
        Main method to handle SCIM requests
        Equivalent to Java ResourceEndpoint.handleRequest()
        """
        try:
            # Parse URL and extract path components
            parsed_url = urlparse(url)
            path_parts = [part for part in parsed_url.path.split('/') if part]
            
            # Remove realm and scim/v2 from path
            if len(path_parts) >= 3 and path_parts[-3] == 'realms' and path_parts[-1] == 'v2':
                resource_path = path_parts[-2:] if len(path_parts) > 3 else []
            else:
                resource_path = path_parts
            
            # Extract query parameters
            query_params = parse_qs(parsed_url.query)
            
            # Route to appropriate handler based on path
            if len(resource_path) == 0:
                # Root endpoint - return service provider config or resource types
                return await self._handleRootEndpoint(httpMethod, context)
            
            elif resource_path[0].lower() == 'users':
                return await self._handleUserRequest(
                    httpMethod, resource_path, requestBody, query_params, context
                )
            
            elif resource_path[0].lower() == 'groups':
                return await self._handleGroupRequest(
                    httpMethod, resource_path, requestBody, query_params, context
                )
            
            elif resource_path[0].lower() == 'resourcetypes':
                return await self._handleResourceTypesRequest(httpMethod, resource_path, context)
            
            elif resource_path[0].lower() == 'serviceproviderconfig':
                return await self._handleServiceProviderConfigRequest(httpMethod, context)
            
            elif resource_path[0].lower() == 'schemas':
                return await self._handleSchemasRequest(httpMethod, resource_path, context)
            
            else:
                return ScimResponse.createErrorResponse(
                    404,
                    f"Resource '{resource_path[0]}' not found",
                    "invalidPath"
                )
                
        except Exception as e:
            return ScimResponse.createErrorResponse(
                500,
                f"Internal server error: {str(e)}",
                "internalError"
            )
    
    async def _handleRootEndpoint(self, httpMethod: str, context: ScimContext) -> ScimResponse:
        """Handle requests to root SCIM endpoint"""
        if httpMethod.upper() == 'GET':
            # Return service provider configuration
            return ScimResponse.createSuccessResponse(self.serviceProviderConfig)
        else:
            return ScimResponse.createErrorResponse(
                405,
                f"Method {httpMethod} not allowed on root endpoint",
                "invalidRequest"
            )
    
    async def _handleUserRequest(
        self,
        httpMethod: str,
        resourcePath: List[str],
        requestBody: Optional[str],
        queryParams: Dict[str, List[str]],
        context: ScimContext
    ) -> ScimResponse:
        """Handle User resource requests"""
        method = httpMethod.upper()
        
        if len(resourcePath) == 1:
            # /Users
            if method == 'GET':
                # List users
                return await self.userHandler.listUsers(queryParams, context)
            elif method == 'POST':
                # Create user
                if not requestBody:
                    return ScimResponse.createErrorResponse(400, "Request body required", "invalidRequest")
                return await self.userHandler.createUser(requestBody, context)
            else:
                return ScimResponse.createErrorResponse(405, f"Method {method} not allowed", "invalidRequest")
        
        elif len(resourcePath) == 2:
            # /Users/{id}
            userId = resourcePath[1]
            if method == 'GET':
                # Get user by ID
                return await self.userHandler.getUser(userId, context)
            elif method == 'PUT':
                # Update user
                if not requestBody:
                    return ScimResponse.createErrorResponse(400, "Request body required", "invalidRequest")
                return await self.userHandler.updateUser(userId, requestBody, context)
            elif method == 'PATCH':
                # Patch user
                if not requestBody:
                    return ScimResponse.createErrorResponse(400, "Request body required", "invalidRequest")
                return await self.userHandler.patchUser(userId, requestBody, context)
            elif method == 'DELETE':
                # Delete user
                return await self.userHandler.deleteUser(userId, context)
            else:
                return ScimResponse.createErrorResponse(405, f"Method {method} not allowed", "invalidRequest")
        
        else:
            return ScimResponse.createErrorResponse(404, "Invalid user endpoint", "invalidPath")
    
    async def _handleGroupRequest(
        self,
        httpMethod: str,
        resourcePath: List[str],
        requestBody: Optional[str],
        queryParams: Dict[str, List[str]],
        context: ScimContext
    ) -> ScimResponse:
        """Handle Group resource requests"""
        method = httpMethod.upper()
        
        if len(resourcePath) == 1:
            # /Groups
            if method == 'GET':
                # List groups
                return await self.groupHandler.listGroups(queryParams, context)
            elif method == 'POST':
                # Create group
                if not requestBody:
                    return ScimResponse.createErrorResponse(400, "Request body required", "invalidRequest")
                return await self.groupHandler.createGroup(requestBody, context)
            else:
                return ScimResponse.createErrorResponse(405, f"Method {method} not allowed", "invalidRequest")
        
        elif len(resourcePath) == 2:
            # /Groups/{id}
            groupId = resourcePath[1]
            if method == 'GET':
                # Get group by ID
                return await self.groupHandler.getGroup(groupId, context)
            elif method == 'PUT':
                # Update group
                if not requestBody:
                    return ScimResponse.createErrorResponse(400, "Request body required", "invalidRequest")
                return await self.groupHandler.updateGroup(groupId, requestBody, context)
            elif method == 'PATCH':
                # Patch group
                if not requestBody:
                    return ScimResponse.createErrorResponse(400, "Request body required", "invalidRequest")
                return await self.groupHandler.patchGroup(groupId, requestBody, context)
            elif method == 'DELETE':
                # Delete group
                return await self.groupHandler.deleteGroup(groupId, context)
            else:
                return ScimResponse.createErrorResponse(405, f"Method {method} not allowed", "invalidRequest")
        
        else:
            return ScimResponse.createErrorResponse(404, "Invalid group endpoint", "invalidPath")
    
    async def _handleResourceTypesRequest(
        self,
        httpMethod: str,
        resourcePath: List[str],
        context: ScimContext
    ) -> ScimResponse:
        """Handle ResourceTypes endpoint"""
        if httpMethod.upper() != 'GET':
            return ScimResponse.createErrorResponse(405, f"Method {httpMethod} not allowed", "invalidRequest")
        
        if len(resourcePath) == 1:
            # Return all resource types
            response = ScimListResponse(
                totalResults=len(self.resourceTypes),
                startIndex=1,
                itemsPerPage=len(self.resourceTypes),
                Resources=self.resourceTypes
            )
            return ScimResponse.createSuccessResponse(response)
        
        elif len(resourcePath) == 2:
            # Return specific resource type
            resourceTypeId = resourcePath[1]
            for rt in self.resourceTypes:
                if rt.id == resourceTypeId:
                    return ScimResponse.createSuccessResponse(rt)
            
            return ScimResponse.createErrorResponse(404, f"ResourceType '{resourceTypeId}' not found", "notFound")
        
        else:
            return ScimResponse.createErrorResponse(404, "Invalid ResourceTypes endpoint", "invalidPath")
    
    async def _handleServiceProviderConfigRequest(self, httpMethod: str, context: ScimContext) -> ScimResponse:
        """Handle ServiceProviderConfig endpoint"""
        if httpMethod.upper() != 'GET':
            return ScimResponse.createErrorResponse(405, f"Method {httpMethod} not allowed", "invalidRequest")
        
        return ScimResponse.createSuccessResponse(self.serviceProviderConfig)
    
    async def _handleSchemasRequest(
        self,
        httpMethod: str,
        resourcePath: List[str],
        context: ScimContext
    ) -> ScimResponse:
        """Handle Schemas endpoint"""
        if httpMethod.upper() != 'GET':
            return ScimResponse.createErrorResponse(405, f"Method {httpMethod} not allowed", "invalidRequest")
        
        # For now, return basic schemas list
        schemas = [
            {
                "id": "urn:ietf:params:scim:schemas:core:2.0:User",
                "name": "User",
                "description": "User Account",
                "attributes": []
            },
            {
                "id": "urn:ietf:params:scim:schemas:core:2.0:Group",
                "name": "Group",
                "description": "Group",
                "attributes": []
            }
        ]
        
        if len(resourcePath) == 1:
            # Return all schemas
            response = ScimListResponse(
                totalResults=len(schemas),
                startIndex=1,
                itemsPerPage=len(schemas),
                Resources=schemas
            )
            return ScimResponse.createSuccessResponse(response)
        
        elif len(resourcePath) == 2:
            # Return specific schema
            schemaId = resourcePath[1]
            for schema in schemas:
                if schema["id"] == schemaId:
                    return ScimResponse.createSuccessResponse(schema)
            
            return ScimResponse.createErrorResponse(404, f"Schema '{schemaId}' not found", "notFound")
        
        else:
            return ScimResponse.createErrorResponse(404, "Invalid Schemas endpoint", "invalidPath")
    
    def _initializeResourceTypes(self) -> List[ScimResourceType]:
        """Initialize SCIM Resource Types"""
        baseUrl = "/realms/{realm}/scim/v2"
        
        userResourceType = ScimResourceType(
            id="User",
            name="User",
            endpoint=f"{baseUrl}/Users",
            description="User Account",
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            meta=ScimMeta(
                resourceType="ResourceType",
                location=f"{baseUrl}/ResourceTypes/User"
            )
        )
        
        groupResourceType = ScimResourceType(
            id="Group",
            name="Group",
            endpoint=f"{baseUrl}/Groups",
            description="Group",
            schema="urn:ietf:params:scim:schemas:core:2.0:Group",
            meta=ScimMeta(
                resourceType="ResourceType",
                location=f"{baseUrl}/ResourceTypes/Group"
            )
        )
        
        return [userResourceType, groupResourceType]
    
    def _initializeServiceProviderConfig(self) -> ScimServiceProviderConfig:
        """Initialize SCIM Service Provider Configuration"""
        return ScimServiceProviderConfig(
            documentationUri="https://tools.ietf.org/html/rfc7644",
            meta=ScimMeta(
                resourceType="ServiceProviderConfig",
                location="/realms/{realm}/scim/v2/ServiceProviderConfig"
            )
        )

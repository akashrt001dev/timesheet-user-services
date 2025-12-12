from typing import List, Optional, Dict, Any
import json
from datetime import datetime

from app.scim.ScimContext import ScimContext
from app.scim.ScimResponse import ScimResponse
from app.services.UserService import UserService
from app.models.scim.ScimModels import (
    ScimGroup, ScimListResponse, ScimError, ScimPatchRequest, ScimMeta
)

class GroupHandler:
    """
    Python equivalent of Java GroupHandler for SCIM Group operations
    Handles SCIM Group resource operations
    """
    
    def __init__(self, userService: UserService):
        self.userService = userService
    
    async def createGroup(self, requestBody: str, context: ScimContext) -> ScimResponse:
        """
        Create a new SCIM Group
        Equivalent to Java createResource method
        """
        try:
            # Parse request body
            groupData = json.loads(requestBody)
            scimGroup = ScimGroup(**groupData)
            
            # Validate required fields
            if not scimGroup.displayName:
                return ScimResponse.createErrorResponse(
                    400,
                    "displayName is required",
                    "invalidValue"
                )
            
            # Create group via UserService
            createdGroup = await self.userService.createGroupFromScimResource(scimGroup)
            
            # Set metadata
            createdGroup.meta = ScimMeta(
                resourceType="Group",
                created=datetime.utcnow(),
                lastModified=datetime.utcnow(),
                location=f"{context.getBaseUrl()}/Groups/{createdGroup.id}"
            )
            
            return ScimResponse.createSuccessResponse(createdGroup, 201)
            
        except json.JSONDecodeError:
            return ScimResponse.createErrorResponse(
                400,
                "Invalid JSON in request body",
                "invalidSyntax"
            )
        except ValueError as e:
            return ScimResponse.createErrorResponse(
                400,
                str(e),
                "invalidValue"
            )
        except Exception as e:
            return ScimResponse.createErrorResponse(
                500,
                f"Failed to create group: {str(e)}",
                "internalError"
            )
    
    async def getGroup(self, groupId: str, context: ScimContext) -> ScimResponse:
        """
        Get a SCIM Group by ID
        Equivalent to Java getResource method
        """
        try:
            group = await self.userService.getScimGroupById(groupId)
            
            if not group:
                return ScimResponse.createErrorResponse(
                    404,
                    f"Group with id '{groupId}' not found",
                    "notFound"
                )
            
            # Set metadata
            group.meta = ScimMeta(
                resourceType="Group",
                location=f"{context.getBaseUrl()}/Groups/{group.id}"
            )
            
            return ScimResponse.createSuccessResponse(group)
            
        except Exception as e:
            return ScimResponse.createErrorResponse(
                500,
                f"Failed to get group: {str(e)}",
                "internalError"
            )
    
    async def listGroups(self, queryParams: Dict[str, List[str]], context: ScimContext) -> ScimResponse:
        """
        List SCIM Groups with pagination and filtering
        Equivalent to Java listResources method
        """
        try:
            # Extract query parameters
            startIndex = int(queryParams.get('startIndex', ['1'])[0])
            count = int(queryParams.get('count', ['100'])[0])
            filter_expr = queryParams.get('filter', [None])[0]
            
            # Get groups from service
            groups = await self.userService.getScimGroupList()
            
            # Apply filtering if provided
            if filter_expr:
                groups = self._applyFilter(groups, filter_expr)
            
            # Apply pagination
            totalResults = len(groups)
            endIndex = min(startIndex + count - 1, totalResults)
            paginatedGroups = groups[startIndex-1:endIndex] if totalResults > 0 else []
            
            # Set metadata for each group
            for group in paginatedGroups:
                group.meta = ScimMeta(
                    resourceType="Group",
                    location=f"{context.getBaseUrl()}/Groups/{group.id}"
                )
            
            # Create list response
            response = ScimListResponse(
                totalResults=totalResults,
                startIndex=startIndex,
                itemsPerPage=len(paginatedGroups),
                Resources=paginatedGroups
            )
            
            return ScimResponse.createSuccessResponse(response)
            
        except ValueError as e:
            return ScimResponse.createErrorResponse(
                400,
                str(e),
                "invalidValue"
            )
        except Exception as e:
            return ScimResponse.createErrorResponse(
                500,
                f"Failed to list groups: {str(e)}",
                "internalError"
            )
    
    async def updateGroup(self, groupId: str, requestBody: str, context: ScimContext) -> ScimResponse:
        """
        Update a SCIM Group (full update)
        Equivalent to Java updateResource method
        """
        try:
            # Parse request body
            groupData = json.loads(requestBody)
            scimGroup = ScimGroup(**groupData)
            scimGroup.id = groupId  # Ensure ID from path is used
            
            # Update group via UserService
            updatedGroup = await self.userService.updateScimGroup(scimGroup)
            
            if not updatedGroup:
                return ScimResponse.createErrorResponse(
                    404,
                    f"Group with id '{groupId}' not found",
                    "notFound"
                )
            
            # Set metadata
            updatedGroup.meta = ScimMeta(
                resourceType="Group",
                lastModified=datetime.utcnow(),
                location=f"{context.getBaseUrl()}/Groups/{updatedGroup.id}"
            )
            
            return ScimResponse.createSuccessResponse(updatedGroup)
            
        except json.JSONDecodeError:
            return ScimResponse.createErrorResponse(
                400,
                "Invalid JSON in request body",
                "invalidSyntax"
            )
        except ValueError as e:
            return ScimResponse.createErrorResponse(
                400,
                str(e),
                "invalidValue"
            )
        except Exception as e:
            return ScimResponse.createErrorResponse(
                500,
                f"Failed to update group: {str(e)}",
                "internalError"
            )
    
    async def patchGroup(self, groupId: str, requestBody: str, context: ScimContext) -> ScimResponse:
        """
        Patch a SCIM Group (partial update)
        Equivalent to Java patchResource method
        """
        try:
            # Parse request body
            patchData = json.loads(requestBody)
            patchRequest = ScimPatchRequest(**patchData)
            
            # Apply patch operations via UserService
            updatedGroup = await self.userService.patchScimGroupById(groupId, patchRequest)
            
            if not updatedGroup:
                return ScimResponse.createErrorResponse(
                    404,
                    f"Group with id '{groupId}' not found",
                    "notFound"
                )
            
            # Set metadata
            updatedGroup.meta = ScimMeta(
                resourceType="Group",
                lastModified=datetime.utcnow(),
                location=f"{context.getBaseUrl()}/Groups/{updatedGroup.id}"
            )
            
            return ScimResponse.createSuccessResponse(updatedGroup)
            
        except json.JSONDecodeError:
            return ScimResponse.createErrorResponse(
                400,
                "Invalid JSON in request body",
                "invalidSyntax"
            )
        except ValueError as e:
            return ScimResponse.createErrorResponse(
                400,
                str(e),
                "invalidValue"
            )
        except Exception as e:
            return ScimResponse.createErrorResponse(
                500,
                f"Failed to patch group: {str(e)}",
                "internalError"
            )
    
    async def deleteGroup(self, groupId: str, context: ScimContext) -> ScimResponse:
        """
        Delete a SCIM Group
        Equivalent to Java deleteResource method
        """
        try:
            # Delete group via UserService
            await self.userService.deleteScimGroupById(groupId)
            
            # Return 204 No Content for successful deletion
            return ScimResponse(httpStatus=204)
            
        except ValueError as e:
            if "not found" in str(e).lower():
                return ScimResponse.createErrorResponse(
                    404,
                    f"Group with id '{groupId}' not found",
                    "notFound"
                )
            else:
                return ScimResponse.createErrorResponse(
                    400,
                    str(e),
                    "invalidValue"
                )
        except Exception as e:
            return ScimResponse.createErrorResponse(
                500,
                f"Failed to delete group: {str(e)}",
                "internalError"
            )
    
    def _applyFilter(self, groups: List[ScimGroup], filter_expr: str) -> List[ScimGroup]:
        """
        Apply SCIM filter expression to group list
        This is a simplified implementation - in production you'd use a proper SCIM filter parser
        """
        # For now, support simple displayName filters like: displayName eq "Administrators"
        if "displayName eq" in filter_expr:
            # Extract the displayName value
            parts = filter_expr.split("displayName eq")
            if len(parts) > 1:
                displayName = parts[1].strip().strip('"')
                return [group for group in groups if group.displayName == displayName]
        
        # Return all groups if no supported filter is found
        return groups
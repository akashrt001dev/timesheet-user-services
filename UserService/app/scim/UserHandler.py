from typing import List, Optional, Dict, Any
import json
from datetime import datetime

from app.scim.ScimContext import ScimContext
from app.scim.ScimResponse import ScimResponse
from app.services.UserService import UserService
from app.models.scim.ScimModels import (
    ScimUser, ScimListResponse, ScimError, ScimPatchRequest, ScimMeta
)

class UserHandler:
    """
    Python equivalent of Java UserHandler for SCIM User operations
    Handles SCIM User resource operations
    """
    
    def __init__(self, userService: UserService):
        self.userService = userService
    
    async def createUser(self, requestBody: str, context: ScimContext) -> ScimResponse:
        """
        Create a new SCIM User
        Equivalent to Java createResource method
        """
        try:
            # Parse request body
            userData = json.loads(requestBody)
            scimUser = ScimUser(**userData)
            
            # Validate required fields
            if not scimUser.userName:
                return ScimResponse.createErrorResponse(
                    400,
                    "userName is required",
                    "invalidValue"
                )
            
            # Create user via UserService
            createdUser = await self.userService.createNewUserFromScimResource(scimUser)
            
            # Set metadata
            createdUser.meta = ScimMeta(
                resourceType="User",
                created=datetime.utcnow(),
                lastModified=datetime.utcnow(),
                location=f"{context.getBaseUrl()}/Users/{createdUser.id}"
            )
            
            return ScimResponse.createSuccessResponse(createdUser, 201)
            
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
                f"Failed to create user: {str(e)}",
                "internalError"
            )
    
    async def getUser(self, userId: str, context: ScimContext) -> ScimResponse:
        """
        Get a SCIM User by ID
        Equivalent to Java getResource method
        """
        try:
            user = await self.userService.getUserForScimById(userId)
            
            if not user:
                return ScimResponse.createErrorResponse(
                    404,
                    f"User with id '{userId}' not found",
                    "notFound"
                )
            
            # Set metadata
            user.meta = ScimMeta(
                resourceType="User",
                location=f"{context.getBaseUrl()}/Users/{user.id}"
            )
            
            return ScimResponse.createSuccessResponse(user)
            
        except Exception as e:
            return ScimResponse.createErrorResponse(
                500,
                f"Failed to get user: {str(e)}",
                "internalError"
            )
    
    async def listUsers(self, queryParams: Dict[str, List[str]], context: ScimContext) -> ScimResponse:
        """
        List SCIM Users with pagination and filtering
        Equivalent to Java listResources method
        """
        try:
            # Extract query parameters
            startIndex = int(queryParams.get('startIndex', ['1'])[0])
            count = int(queryParams.get('count', ['100'])[0])
            filter_expr = queryParams.get('filter', [None])[0]
            
            # Get users from service
            users = await self.userService.getUserScimList()
            
            # Apply filtering if provided
            if filter_expr:
                users = self._applyFilter(users, filter_expr)
            
            # Apply pagination
            totalResults = len(users)
            endIndex = min(startIndex + count - 1, totalResults)
            paginatedUsers = users[startIndex-1:endIndex] if totalResults > 0 else []
            
            # Set metadata for each user
            for user in paginatedUsers:
                user.meta = ScimMeta(
                    resourceType="User",
                    location=f"{context.getBaseUrl()}/Users/{user.id}"
                )
            
            # Create list response
            response = ScimListResponse(
                totalResults=totalResults,
                startIndex=startIndex,
                itemsPerPage=len(paginatedUsers),
                Resources=paginatedUsers
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
                f"Failed to list users: {str(e)}",
                "internalError"
            )
    
    async def updateUser(self, userId: str, requestBody: str, context: ScimContext) -> ScimResponse:
        """
        Update a SCIM User (full update)
        Equivalent to Java updateResource method
        """
        try:
            # Parse request body
            userData = json.loads(requestBody)
            scimUser = ScimUser(**userData)
            scimUser.id = userId  # Ensure ID from path is used
            
            # Update user via UserService
            updatedUser = await self.userService.updateUserByScimResource(scimUser)
            
            if not updatedUser:
                return ScimResponse.createErrorResponse(
                    404,
                    f"User with id '{userId}' not found",
                    "notFound"
                )
            
            # Set metadata
            updatedUser.meta = ScimMeta(
                resourceType="User",
                lastModified=datetime.utcnow(),
                location=f"{context.getBaseUrl()}/Users/{updatedUser.id}"
            )
            
            return ScimResponse.createSuccessResponse(updatedUser)
            
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
                f"Failed to update user: {str(e)}",
                "internalError"
            )
    
    async def patchUser(self, userId: str, requestBody: str, context: ScimContext) -> ScimResponse:
        """
        Patch a SCIM User (partial update)
        Equivalent to Java patchResource method
        """
        try:
            # Parse request body
            patchData = json.loads(requestBody)
            patchRequest = ScimPatchRequest(**patchData)
            
            # Apply patch operations via UserService
            updatedUser = await self.userService.patchUserByScimId(userId, patchRequest)
            
            if not updatedUser:
                return ScimResponse.createErrorResponse(
                    404,
                    f"User with id '{userId}' not found",
                    "notFound"
                )
            
            # Set metadata
            updatedUser.meta = ScimMeta(
                resourceType="User",
                lastModified=datetime.utcnow(),
                location=f"{context.getBaseUrl()}/Users/{updatedUser.id}"
            )
            
            return ScimResponse.createSuccessResponse(updatedUser)
            
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
                f"Failed to patch user: {str(e)}",
                "internalError"
            )
    
    async def deleteUser(self, userId: str, context: ScimContext) -> ScimResponse:
        """
        Delete a SCIM User
        Equivalent to Java deleteResource method
        """
        try:
            # Delete user via UserService
            await self.userService.deleteUserByScimId(userId)
            
            # Return 204 No Content for successful deletion
            return ScimResponse(httpStatus=204)
            
        except ValueError as e:
            if "not found" in str(e).lower():
                return ScimResponse.createErrorResponse(
                    404,
                    f"User with id '{userId}' not found",
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
                f"Failed to delete user: {str(e)}",
                "internalError"
            )
    
    def _applyFilter(self, users: List[ScimUser], filter_expr: str) -> List[ScimUser]:
        """
        Apply SCIM filter expression to user list
        This is a simplified implementation - in production you'd use a proper SCIM filter parser
        """
        # For now, support simple userName filters like: userName eq "john@example.com"
        if "userName eq" in filter_expr:
            # Extract the username value
            parts = filter_expr.split("userName eq")
            if len(parts) > 1:
                username = parts[1].strip().strip('"')
                return [user for user in users if user.userName == username]
        
        # Return all users if no supported filter is found
        return users
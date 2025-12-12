from typing import Dict, Any, Optional
import json
from datetime import datetime

class ScimResponse:
    """
    Python equivalent of de.captaingoldfish.scim.sdk.common.response.ScimResponse
    Represents a SCIM response with status, headers, and body
    """
    
    def __init__(
        self,
        httpStatus: int = 200,
        httpHeaders: Optional[Dict[str, str]] = None,
        responseBody: Optional[Any] = None
    ):
        self.httpStatus = httpStatus
        self.httpHeaders = httpHeaders or {}
        self.responseBody = responseBody
        
        # Set default content type if not provided
        if "content-type" not in self.httpHeaders:
            self.httpHeaders["content-type"] = "application/scim+json"
    
    def setHttpStatus(self, status: int) -> None:
        """Set HTTP status code"""
        self.httpStatus = status
    
    def getHttpStatus(self) -> int:
        """Get HTTP status code"""
        return self.httpStatus
    
    def setHttpHeader(self, name: str, value: str) -> None:
        """Set HTTP header"""
        self.httpHeaders[name.lower()] = value
    
    def getHttpHeader(self, name: str) -> Optional[str]:
        """Get HTTP header"""
        return self.httpHeaders.get(name.lower())
    
    def getHttpHeaders(self) -> Dict[str, str]:
        """Get all HTTP headers"""
        return self.httpHeaders
    
    def setResponseBody(self, body: Any) -> None:
        """Set response body"""
        self.responseBody = body
    
    def getResponseBody(self) -> Optional[Any]:
        """Get response body"""
        return self.responseBody
    
    def toPrettyString(self) -> str:
        """Convert response body to pretty-printed JSON string"""
        if self.responseBody is None:
            return ""
        
        if isinstance(self.responseBody, str):
            try:
                # Try to parse and re-format JSON
                parsed = json.loads(self.responseBody)
                return json.dumps(parsed, indent=2, default=str)
            except json.JSONDecodeError:
                return self.responseBody
        else:
            # Convert object to JSON
            if hasattr(self.responseBody, 'dict'):
                # Pydantic model
                return json.dumps(self.responseBody.dict(), indent=2, default=str)
            elif hasattr(self.responseBody, '__dict__'):
                # Regular Python object
                return json.dumps(self.responseBody.__dict__, indent=2, default=str)
            else:
                return json.dumps(self.responseBody, indent=2, default=str)
    
    def toString(self) -> str:
        """Convert response body to JSON string"""
        if self.responseBody is None:
            return ""
        
        if isinstance(self.responseBody, str):
            return self.responseBody
        else:
            if hasattr(self.responseBody, 'dict'):
                # Pydantic model
                return json.dumps(self.responseBody.dict(), default=str)
            elif hasattr(self.responseBody, '__dict__'):
                # Regular Python object
                return json.dumps(self.responseBody.__dict__, default=str)
            else:
                return json.dumps(self.responseBody, default=str)
    
    def isError(self) -> bool:
        """Check if this is an error response"""
        return self.httpStatus >= 400
    
    def getContentLength(self) -> int:
        """Get content length"""
        content = self.toString()
        return len(content.encode('utf-8'))
    
    @staticmethod
    def createErrorResponse(status: int, detail: str, scimType: Optional[str] = None) -> 'ScimResponse':
        """Create an error response"""
        from app.models.scim.ScimModels import ScimError
        
        error = ScimError(
            detail=detail,
            status=str(status),
            scimType=scimType
        )
        
        return ScimResponse(
            httpStatus=status,
            responseBody=error
        )
    
    @staticmethod
    def createSuccessResponse(body: Any, status: int = 200) -> 'ScimResponse':
        """Create a success response"""
        return ScimResponse(
            httpStatus=status,
            responseBody=body
        )

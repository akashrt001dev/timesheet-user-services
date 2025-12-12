from typing import Dict, Any, Optional
from fastapi import Request
import json

class ScimContext:
    """
    Python equivalent of de.captaingoldfish.scim.sdk.server.endpoints.Context
    This is an exact translation of the Java Context class used in SCIM operations
    """
    
    def __init__(self, request: Request, realm: str, scimAuthentication: Any = None):
        """
        Constructor equivalent to Java: new Context(scimAuthentication)
        """
        self.request = request
        self.realm = realm
        self.scimAuthentication = scimAuthentication
        self.attributes: Dict[str, Any] = {}
        self.httpHeaders: Dict[str, str] = {}
        
        # Extract headers from request (equivalent to Java headers extraction)
        for name, value in request.headers.items():
            self.httpHeaders[name.lower()] = value
    
    def setAttribute(self, key: str, value: Any) -> None:
        """Set a context attribute - equivalent to Java setAttribute"""
        self.attributes[key] = value
    
    def getAttribute(self, key: str) -> Optional[Any]:
        """Get a context attribute - equivalent to Java getAttribute"""
        return self.attributes.get(key)
    
    def getHttpHeaders(self) -> Dict[str, str]:
        """Get HTTP headers - equivalent to Java getHttpHeaders"""
        return self.httpHeaders
    
    def getHttpHeader(self, name: str) -> Optional[str]:
        """Get a specific HTTP header - equivalent to Java getHttpHeader"""
        return self.httpHeaders.get(name.lower())
    
    def getAuthentication(self) -> Any:
        """Get authentication object - equivalent to Java getAuthentication"""
        return self.scimAuthentication
    
    def getRealm(self) -> str:
        """Get the realm - equivalent to Java getRealm"""
        return self.realm
    
    def getBaseUrl(self) -> str:
        """Get the base URL for SCIM endpoints"""
        base_url = f"{self.request.url.scheme}://{self.request.url.netloc}"
        return f"{base_url}/realms/{self.realm}/scim/v2"
    
    def getFullUrl(self) -> str:
        """Get the full request URL"""
        return str(self.request.url)

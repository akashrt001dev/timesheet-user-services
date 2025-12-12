from fastapi import Request, status
from fastapi.responses import JSONResponse

# --- Custom Exception Classes ---
# These classes are direct Python equivalents of your Java exception classes.
# They inherit from Python's base Exception class.

class InvalidTenantException(Exception):
    """Custom exception for invalid tenant errors."""
    def __init__(self, message: str = "Invalid tenant provided"):
        self.message = message
        super().__init__(self.message)

class InvalidUserException(Exception):
    """Custom exception for invalid user data."""
    def __init__(self, message: str = "Invalid user data"):
        self.message = message
        super().__init__(self.message)

class InvalidUserTenantException(Exception):
    """Custom exception for a user not belonging to a specific tenant."""
    def __init__(self, message: str = "User does not belong to the specified tenant"):
        self.message = message
        super().__init__(self.message)

class ResourceNotFoundException(Exception):
    """Custom exception for a resource that cannot be found."""
    def __init__(self, message: str = "Resource not found"):
        self.message = message
        super().__init__(self.message)

class UserAlreadyExistException(Exception):
    """Custom exception for attempting to create a user that already exists."""
    def __init__(self, message: str = "User with the given identifier already exists"):
        self.message = message
        super().__init__(self.message)


# --- FastAPI Exception Handlers ---
# These functions tell FastAPI how to convert your custom exceptions into
# standard HTTP JSON error responses.

async def resource_not_found_exception_handler(request: Request, exc: ResourceNotFoundException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message},
    )

async def user_already_exist_exception_handler(request: Request, exc: UserAlreadyExistException):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message},
    )

async def invalid_user_exception_handler(request: Request, exc: InvalidUserException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message},
    )

async def invalid_tenant_exception_handler(request: Request, exc: InvalidTenantException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message},
    )

async def invalid_user_tenant_exception_handler(request: Request, exc: InvalidUserTenantException):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": exc.message},
    )

def add_exception_handlers(app):
    """
    A helper function to add all custom exception handlers to the FastAPI app instance.
    You would call this in your main.py file.
    """
    app.add_exception_handler(ResourceNotFoundException, resource_not_found_exception_handler)
    app.add_exception_handler(UserAlreadyExistException, user_already_exist_exception_handler)
    app.add_exception_handler(InvalidUserException, invalid_user_exception_handler)
    app.add_exception_handler(InvalidTenantException, invalid_tenant_exception_handler)
    app.add_exception_handler(InvalidUserTenantException, invalid_user_tenant_exception_handler)

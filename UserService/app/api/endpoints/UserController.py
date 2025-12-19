from fastapi import APIRouter, Depends, HTTPException, Header, Path, Query, status, File, UploadFile, Form
import json
from typing import List, Optional
from app.models.DTO.UserDTO import UserDTO
from app.models.DTO.UserDTOList import UserDTOList
from app.models.DTO.UserListDTO import UserListDTO
from app.models.DTO.UserRoleDTO import UserRoleDTO
from app.models.DTO.UserPasswordDTO import UserPasswordDTO
from app.models.DTO.BillingInfoDTO import BillingInfoDTO
from app.models.DTO.ChangePasswordDTO import ChangePasswordDTO
from app.models.DTO.ProfilePictureDTO import ProfilePictureDTO
from app.models.DTO.UpdatePasswordDTO import UpdatePasswordDTO
from app.models.DTO.UserSsoIdDTO import UserSsoIdDTO
from app.models.DTO.AccessScopeResponseDTO import AccessScopeResponseDTO
from app.models.aggregates.root.User import User
from app.models.valueobjects.BlockOrDeactivateAction import BlockOrDeactivateAction
from app.models.valueobjects.Email import Email
from app.services.UserService import UserService
from app.security.JwtUtil import JwtUtil
from app.repositories.UserRepository import UserRepository
from app.security.JwtUserDetailService import JwtUserDetailService

router = APIRouter(prefix="/user")

class UserController:
    """
    Python equivalent of Java UserController
    FastAPI router for user management endpoints
    """
    
    def __init__(self):
        # Properties will be set by dependency injection
        self.userService = None
        self.userDetailService = None
        self.jwtUtil = None
        self.userRepository = None

# Global controller instance (would be dependency injected in real app)
user_controller = None

def get_user_controller() -> UserController:
    global user_controller
    if user_controller is None:
        # Create controller instance
        user_controller = UserController()
        
        # Properties will be injected in startup when database and dependencies are available
        user_controller.userService = None
        user_controller.userRepository = None
        user_controller.userDetailService = None
        user_controller.jwtUtil = None
        
    return user_controller

@router.get("/{id}/notify")
async def notifyUser(
    id: str = Path(alias="id"),
    X_Authorization: str = Header(alias="X-Authorization"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: UserController = Depends(get_user_controller)
):
    """
    Equivalent to Java: @GetMapping("/{id}/notify")
    public ResponseEntity<?> notifyUser(@PathVariable("id") String userId, @RequestHeader(value = "X-Authorization") String authorization, @RequestHeader(value = "X-tenantID") String tenantId)
    """
    try:
        result = await controller.userService.notifyUser(id)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/role")
async def addRoleToUser(
    userRoleDTO: UserRoleDTO,
    X_Authorization: str = Header(alias="X-Authorization"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: UserController = Depends(get_user_controller)
) -> str:
    """
    Equivalent to Java: @PutMapping("/role")
    public ResponseEntity<String> addRoleToUser(@RequestBody UserRoleDTO userRoleDTO, @RequestHeader(value = "X-Authorization") String authorization, @RequestHeader(value = "X-tenantID") String tenantId)
    
    Adds roles to a user. Validates that the user exists in the specified tenant before adding roles.
    Returns success message if roles are added successfully.
    """
    try:
        result = await controller.userService.addRoleToUser(userRoleDTO, X_tenantID)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/register")
async def registerNewUser(
    userDTO: UserDTO,
    X_Authorization: Optional[str] = Header(default=None, alias="X-Authorization"),
    Authorization: Optional[str] = Header(default=None, alias="Authorization"),
    controller: UserController = Depends(get_user_controller)
):
    """
    Equivalent to Java: @PostMapping("/register")
    public ResponseEntity<?> registerNewUser(@RequestHeader(value = "X-Authorization") String authorization,@RequestBody UserDTO userDTO) throws Exception
    
    Registers a new user in the system. Requires authentication via X-Authorization or Authorization header.
    Extracts username from OAuth JWT token, creates the user with provided details, and sends activation email.
    
    Returns:
        - 200: User successfully registered with user data
        - 401: Missing or invalid authorization header
        - 400: Registration failed (validation errors, duplicate user, etc.)
    """
    try:
        auth_header = X_Authorization or Authorization
        if not auth_header:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
        result = await controller.userService.registerNewUser(auth_header, userDTO)
        return {"status": "success", "data": result}
    except HTTPException as he:
        # Preserve original status code (e.g., 401 for token issues)
        raise he
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/registerUserList")
async def registerNewUserList(
    userDTOList: UserDTOList,
    X_Authorization: Optional[str] = Header(default=None, alias="X-Authorization"),
    controller: UserController = Depends(get_user_controller)
) -> str:
    """
    Equivalent to Java: @PostMapping("/registerUserList")
    public ResponseEntity<String> registerNewUserList(@RequestBody UserDTOList userDTOList)
    
    Registers multiple users in a single batch operation. Validates and saves all users in the list.
    Each user undergoes registration validation and password encryption before being saved.
    
    Returns:
        - 200: Success message with count of registered users
        - 400: Registration failed (empty list, validation errors, etc.)
    """
    try:
        result = await controller.userService.registerNewUserList(userDTOList)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("")
async def getUserList(
    X_tenantID: str = Header(alias="X-tenantID"),
    firstName: Optional[str] = Query(None),
    lastName: Optional[str] = Query(None),
    contractID: Optional[str] = Query(None),
    activated: Optional[str] = Query(None),
    userType: Optional[str] = Query(None),
    blocked: Optional[str] = Query(None),
    invited: Optional[str] = Query(None),
    partnerId: Optional[str] = Query(None),
    contractIdOnFile: Optional[str] = Query(None),
    sites: Optional[List[str]] = Query(None),
    sitedepartments: Optional[List[str]] = Query(None),
    userTypes: Optional[List[str]] = Query(None),
    titles: Optional[List[str]] = Query(None),
    searchText: Optional[str] = Query(None),
    offset: int = Query(0),
    limit: int = Query(0),
    controller: UserController = Depends(get_user_controller)
) -> UserListDTO:
    """
    Equivalent to Java: @GetMapping()
    public UserListDTO getUserList(...) - with all the query parameters
    
    Retrieves a filtered and paginated list of users for a specific tenant.
    Supports multiple filter criteria including name, contract, status, user type, sites, departments, titles, and text search.
    Returns UserListDTO containing the list of users and total count.
    
    Query Parameters:
        - firstName, lastName: Filter by user name
        - contractID, contractIdOnFile: Filter by contract
        - activated, blocked, invited: Filter by user status
        - userType, userTypes: Filter by user type(s)
        - partnerId: Filter by partner
        - sites, sitedepartments, titles: Filter by organizational attributes
        - searchText: General text search across user fields
        - offset, limit: Pagination parameters (default limit=0 returns all)
    
    Returns:
        UserListDTO with filtered users and total count
    """
    try:
        result = await controller.userService.getUserList(
            X_tenantID, firstName, lastName, contractID, activated, userType,
            blocked, invited, partnerId, sites, titles, sitedepartments,
            contractIdOnFile, userTypes, searchText, offset, limit
        )
        
        # Transform users in the result to match the expected response format
        if result and hasattr(result, 'users') and result.users:
            transformed_users = []
            for user in result.users:
                # Serialize with all fields including None values (exclude_none=False)
                user_dict = user.model_dump(by_alias=True, exclude_none=False) if hasattr(user, 'model_dump') else user
                
                # Remove npin only if it's None to avoid validation issues
                if "npin" in user_dict and user_dict["npin"] is None:
                    del user_dict["npin"]
                
                # Flatten sites structure - extract sites array from sites.sites
                if "sites" in user_dict and isinstance(user_dict["sites"], dict) and "sites" in user_dict["sites"]:
                    user_dict["sites"] = user_dict["sites"]["sites"]
                
                # Convert avgLoginSession to object structure with milliseconds
                if "avgLoginSession" in user_dict:
                    user_dict["avgLoginSession"] = {"milliseconds": user_dict["avgLoginSession"] if isinstance(user_dict["avgLoginSession"], (int, float)) else 0}
                
                # Ensure title object structure with title and id fields
                if "title" in user_dict and isinstance(user_dict["title"], dict):
                    # Ensure both title and id fields exist
                    if "title" not in user_dict["title"]:
                        user_dict["title"]["title"] = None
                    if "id" not in user_dict["title"]:
                        user_dict["title"]["id"] = None
                else:
                    # If title doesn't exist or isn't a dict, create proper structure
                    user_dict["title"] = {"title": None, "id": None}
                
                # Ensure suffix object structure
                if "name" in user_dict and isinstance(user_dict["name"], dict):
                    if "suffix" not in user_dict["name"]:
                        user_dict["name"]["suffix"] = {"id": None, "suffix": None}
                    elif not isinstance(user_dict["name"]["suffix"], dict):
                        user_dict["name"]["suffix"] = {"id": None, "suffix": None}
                
                # Ensure boolean flags are present
                if "activated" not in user_dict:
                    user_dict["activated"] = False
                if "invited" not in user_dict:
                    user_dict["invited"] = False
                if "blocked" not in user_dict:
                    user_dict["blocked"] = False
                if "deleted" not in user_dict:
                    user_dict["deleted"] = False
                if "personalEmailAddressAllowed" not in user_dict:
                    user_dict["personalEmailAddressAllowed"] = False
                if "executiveAccessLevelNeeded" not in user_dict:
                    user_dict["executiveAccessLevelNeeded"] = False
                if "surrogateEnabled" not in user_dict:
                    user_dict["surrogateEnabled"] = False
                
                transformed_users.append(user_dict)
            
            # Replace users list with transformed dicts
            result.users = transformed_users
        
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/role")
async def getUserListByRole(
    X_Authorization: str = Header(alias="X-Authorization"),
    X_tenantID: str = Header(alias="X-tenantID"),
    role: List[str] = Query(alias="role"),
    controller: UserController = Depends(get_user_controller)
) -> List[User]:
    """
    Equivalent to Java: @GetMapping("/role")
    public List<User> getUserListByRole(@RequestHeader(value = "X-tenantID") String tenantId, @RequestParam(name = "role") List<String> roleName)
    
    Retrieves a list of users filtered by tenant ID and role names.
    Returns all users in the specified tenant who have any of the specified roles.
    """
    try:
        return await controller.userService.getUserListByRole(X_tenantID, role)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("")
async def updateUser(
    userDTO: UserDTO,
    X_Authorization: str = Header(alias="X-Authorization"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: UserController = Depends(get_user_controller)
) -> str:
    """
    Equivalent to Java: @PutMapping()
    public ResponseEntity<String> updateUser(@RequestBody UserDTO userDTO, @RequestHeader(value = "X-tenantID") String tenantId)
    
    Updates an existing user in the specified tenant.
    Validates user ID, email uniqueness, tenant membership, and SSO ID before updating.
    Preserves existing password during update. Returns success message on completion.
    
    Validations:
        - User ID must not be blank
        - User must exist and belong to the specified tenant
        - Email cannot be changed to one already used by another user in tenant
        - SSO ID is required
        - Password is preserved from existing record (not updated via this endpoint)
    
    Request Body:
        UserDTO with all user fields including id, name, email, tenant, roles, etc.
    
    Returns:
        Success message string: "User Updated Successfully"
    
    Raises:
        400: User ID blank, email already exists, SSO ID missing
        404: User not found, user not in tenant
    """
    try:
        # Convert DTO to domain model before passing to service
        user = userDTO.to_domain()
        result = await controller.userService.updateUser(user, X_tenantID)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# NOTE: The dynamic '/{userId}' route must come AFTER all static single-segment routes
# to avoid shadowing them (e.g., '/metadata', '/getUser', '/ListOfId', etc.).

@router.get("/ListOfId")
async def getUserListByListOfId(
    userIds: List[str] = Query(alias="userIds"),
    controller: UserController = Depends(get_user_controller)
) -> List[User]:
    """
    Equivalent to Java: @GetMapping("/ListOfId")
    public List<User> getUserListByListOfId(@RequestParam(name = "userIds") List<String> userIds)
    
    Retrieves a list of users by their IDs. Does not filter by tenant - returns users
    from any tenant if they match the provided user IDs. Useful for batch user retrieval
    across tenant boundaries or for system-level operations.
    
    Query Parameters:
        userIds: List of user ID strings to retrieve
    
    Returns:
        List[User] objects matching the provided IDs
    """
    try:
        return await controller.userService.getUserListByListOfId(userIds)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/ListOfIdAndContractAndSiteAndDepartment")
async def getUserListByListOfIdAndContractAndSiteAndDepartment(
    tenantId: str = Query(),
    X_Authorization: str = Header(alias="X-Authorization"),
    contracts: Optional[List[str]] = Query(None),
    users: Optional[List[str]] = Query(None),
    sites: Optional[List[str]] = Query(None),
    departments: Optional[List[str]] = Query(None),
    controller: UserController = Depends(get_user_controller)
) -> List[User]:
    """
    Equivalent to Java: @GetMapping("/ListOfIdAndContractAndSiteAndDepartment")
    public List<User> getUserListByListOfIdAndContractAndSiteAndDepartment(...)
    
    Retrieves users filtered by multiple criteria: tenant, user IDs, contracts, sites, and departments.
    All filter parameters are optional (except tenantId) and are combined with AND logic.
    Used for complex user queries with organizational hierarchy filtering.
    
    Query Parameters:
        tenantId: Required - filter by tenant ID
        contracts: Optional - filter by contract IDs
        users: Optional - filter by specific user IDs
        sites: Optional - filter by site IDs
        departments: Optional - filter by department IDs
    
    Returns:
        List[User] objects matching all provided filter criteria within the tenant
    """
    try:
        return await controller.userService.getUserListByListOfIdAndContractAndSiteAndDepartment(
            tenantId, contracts, users, sites, departments
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/setpassword")
async def setUserPassword(
    userPasswordDTO: UserPasswordDTO,
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: UserController = Depends(get_user_controller)
) -> str:
    """
    Equivalent to Java: @PostMapping("/setpassword")
    public ResponseEntity<String> setUserPassword(@RequestHeader(value = "X-tenantID") String tenantId,@RequestBody UserPasswordDTO userPasswordDTO)
    
    Sets or updates the password for a user. Encodes the password using BCrypt,
    activates the user account, maintains password history (last 12 passwords),
    and resets password reset tokens. Used during initial password setup or admin password reset.
    
    Request Body:
        UserPasswordDTO containing userId and new password
    
    Business Logic:
        - Validates user exists in tenant
        - Encodes password using BCrypt
        - Sets isActivated = true
        - Adds password to password history list (max 12)
        - Resets hash ID and expiration time for password reset tokens
        - Updates legacy encryptedPassword field for backward compatibility
    
    Returns:
        Success message: "Password set successfully"
    
    Raises:
        404: User not found in tenant
        400: Invalid request data
    """
    try:
        # Service returns the updated User, but Java returns a String response.
        await controller.userService.setUserPassword(X_tenantID, userPasswordDTO)
        return "Password set successfully"
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/metadata")
async def getUsersMetadata(
    X_tenantID: str = Header(alias="X-tenantID"),
    siteId: Optional[str] = Query(None),
    startDate: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
    controller: UserController = Depends(get_user_controller)
):
    """
    Equivalent to Java: @GetMapping("/metadata")
    public ResponseEntity<?> getUsersMetadata(...)
    
    Retrieves user statistics and metadata for a tenant within a date range.
    Returns aggregated data about user registrations, activations, and activity.
    If dates not provided, defaults to last 30 days ending today.
    
    Query Parameters:
        siteId: Optional - filter by specific site
        startDate: Optional - start date (YYYY-MM-DD format), defaults to 30 days ago
        endDate: Optional - end date (YYYY-MM-DD format), defaults to today
    
    Returns:
        Dictionary with user metadata statistics grouped by date or category
    
    Raises:
        400: Invalid date format (must be YYYY-MM-DD)
    """
    try:
        # Provide sensible defaults if dates are not supplied: last 30 days ending today
        if not startDate or not endDate:
            from datetime import datetime, timedelta
            today = datetime.utcnow().date()
            # If endDate provided, parse it; else use today
            if endDate:
                try:
                    end_date_obj = datetime.strptime(endDate, "%Y-%m-%d").date()
                except ValueError:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid endDate format, expected YYYY-MM-DD")
            else:
                end_date_obj = today
            # If startDate provided, parse it; else 30 days before end_date
            if startDate:
                try:
                    start_date_obj = datetime.strptime(startDate, "%Y-%m-%d").date()
                except ValueError:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid startDate format, expected YYYY-MM-DD")
            else:
                start_date_obj = end_date_obj - timedelta(days=30)
            startDate = start_date_obj.strftime("%Y-%m-%d")
            endDate = end_date_obj.strftime("%Y-%m-%d")

        result = await controller.userService.getUsersMetadata(X_tenantID, siteId, startDate, endDate)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/registeredUserMetadata")
async def getRegisteredUsersMetadata(
    X_tenantID: str = Header(alias="X-tenantID"),
    siteId: Optional[str] = Query(None),
    controller: UserController = Depends(get_user_controller)
):
    """
    Equivalent to Java: @GetMapping("/registeredUserMetadata")
    public ResponseEntity<?> getRegisteredUsersMetadata(...)
    
    Retrieves metadata about registered (activated) users in a tenant.
    Returns count and statistics for users who have completed registration
    and activated their accounts. Can be filtered by site.
    
    Query Parameters:
        siteId: Optional - filter by specific site ID
    
    Returns:
        Dictionary with registered user counts and metadata
    """
    try:
        result = await controller.userService.getRegisteredUsersMetadata(X_tenantID, siteId)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/{id}/changePassword")
async def changePassword(
    passwords: ChangePasswordDTO,
    id: str = Path(),
    X_Authorization: str = Header(alias="X-Authorization"),
    controller: UserController = Depends(get_user_controller)
):
    """
    Equivalent to Java: @PutMapping("/{id}/changePassword")
    public ResponseEntity<?> changePassword(...)
    
    Allows an authenticated user to change their own password.
    Validates the old password, checks new password against password history
    (prevents reuse of last 12 passwords), and updates with BCrypt encoding.
    Uses JWT token from X-Authorization header to identify the user.
    
    Path Parameters:
        id: User ID (may be used for additional validation)
    
    Request Body:
        ChangePasswordDTO containing oldPassword and newPassword
    
    Business Logic:
        - Extracts user from JWT token in X-Authorization header
        - Validates old password matches current password
        - Checks new password not in last 12 passwords (password history)
        - Encodes new password with BCrypt
        - Updates password and password history
    
    Returns:
        Success response with updated user data
    
    Raises:
        400: Old password incorrect, new password in history, validation failed
        401: Invalid or missing JWT token
    """
    try:
        result = await controller.userService.changePassword(X_Authorization, passwords)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/{userId}/billingInformation")
async def updateBillingInformation(
    billingInformation: BillingInfoDTO,
    userId: str = Path(alias="userId"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: UserController = Depends(get_user_controller)
) -> int:
    """
    Equivalent to Java: @PutMapping("/{userId}/billingInformation")
    public HttpStatus updateBillingInformation(@PathVariable("userId") String userId, ...)
    
    Updates billing information for a professional services user.
    Sets or modifies billing rates, billing type, and related financial data
    for contractors or service providers. Validates user exists in tenant.
    
    Path Parameters:
        userId: ID of the user to update billing information for
    
    Request Body:
        BillingInfoDTO with billing rate, type, currency, and other financial fields
    
    Returns:
        HTTP status code (typically 200)
    
    Raises:
        404: User not found in tenant
        400: Invalid billing information
    """
    try:
        result = await controller.userService.updateBillingInformation(userId, X_tenantID, billingInformation)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/forgetpassword")
async def forgetPassword(
    email: Email,
    controller: UserController = Depends(get_user_controller)
):
    """
    Equivalent to Java: @PostMapping("/forgetpassword")
    public ResponseEntity<?> forgetPassword(@RequestBody Email email)
    
    Initiates password reset flow for a user who has forgotten their password.
    Generates a unique reset token (hash ID) with expiration time,
    stores it in the user record, and sends a password reset email
    with a link containing the token.
    
    Request Body:
        Email object containing the user's email address
    
    Business Logic:
        - Validates user exists with provided email
        - Generates unique hash ID for password reset
        - Sets expiration time (typically 24 hours)
        - Stores hash ID and expiration in user record
        - Sends password reset email with reset link
    
    Returns:
        Success response confirming email sent
    
    Raises:
        404: User not found with provided email
        400: Email sending failed or invalid email format
    """
    try:
        result = await controller.userService.forgetPassword(email)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/profilePic")
async def AddPicByUserId(
    X_Authorization: str = Header(alias="X-Authorization"),
    X_tenantID: str = Header(alias="X-tenantID"),
    profilePicture: str = Form(..., description="ProfilePictureDTO JSON as string"),
    pictureFile: UploadFile = File(...),
    controller: UserController = Depends(get_user_controller)
) -> str:
    """
    Equivalent to Java: @PostMapping(value="/profilePic",consumes = {MediaType.MULTIPART_FORM_DATA_VALUE})
    public ResponseEntity<String> AddPicByUserId(...)
    
    Uploads a new profile picture for a user. Handles multipart form data with
    both profile metadata (as JSON string) and image file. Uploads to S3 storage,
    generates unique filename, and stores reference in user record.
    
    Form Data:
        profilePicture: JSON string of ProfilePictureDTO (userId, description, etc.)
        pictureFile: Image file upload (JPEG, PNG, etc.)
    
    Business Logic:
        - Parses ProfilePictureDTO from JSON form field
        - Validates image file type and size
        - Generates unique filename with UUID
        - Uploads to S3 bucket (user-profile-pictures)
        - Stores S3 URL and metadata in user's profilePic field
        - Returns success message with S3 URL
    
    Returns:
        Success message with uploaded file URL
    
    Raises:
        400: Invalid file type, file too large, or JSON parsing error
        404: User not found
    """
    try:
        # Parse DTO from JSON string within multipart form
        try:
            profile_dto = ProfilePictureDTO.model_validate_json(profilePicture)  # type: ignore[attr-defined]
        except Exception:
            profile_dto = ProfilePictureDTO(**json.loads(profilePicture))

        result = await controller.userService.AddPicByUserId(X_tenantID, profile_dto, pictureFile)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/profilePic")
async def UpdatePicByUserId(
    X_Authorization: str = Header(alias="X-Authorization"),
    X_tenantID: str = Header(alias="X-tenantID"),
    profilePicture: str = Form(..., description="ProfilePictureDTO JSON as string"),
    pictureFile: UploadFile = File(...),
    controller: UserController = Depends(get_user_controller)
) -> str:
    """
    Equivalent to Java: @PutMapping(value="/profilePic",consumes = {MediaType.MULTIPART_FORM_DATA_VALUE})
    public ResponseEntity<String> UpdatePicByUserId(...)
    
    Updates an existing profile picture for a user. Deletes the old image from S3,
    uploads the new image, and updates the user record with the new S3 URL.
    Handles multipart form data with metadata and image file.
    
    Form Data:
        profilePicture: JSON string of ProfilePictureDTO (userId, description, etc.)
        pictureFile: New image file upload (JPEG, PNG, etc.)
    
    Business Logic:
        - Retrieves existing user and profile picture
        - Deletes old image from S3 if exists
        - Uploads new image to S3 with unique filename
        - Updates user's profilePic field with new S3 URL and metadata
        - Returns success message
    
    Returns:
        Success message with updated file URL
    
    Raises:
        400: Invalid file type, file too large, or JSON parsing error
        404: User not found
    """
    try:
        # Parse DTO from JSON string within multipart form
        try:
            profile_dto = ProfilePictureDTO.model_validate_json(profilePicture)  # type: ignore[attr-defined]
        except Exception:
            profile_dto = ProfilePictureDTO(**json.loads(profilePicture))

        result = await controller.userService.UpdatePicByUserId(X_tenantID, profile_dto, pictureFile)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/updatepassword")
async def setPassword(
    passwordDTO: UpdatePasswordDTO,
    X_Authorization: str = Header(alias="X-Authorization"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: UserController = Depends(get_user_controller)
):
    """
    Equivalent to Java: @PostMapping("/updatepassword")
    public ResponseEntity<?> setPassword(@RequestHeader(value ="X-tenantID") String tenantId, @RequestBody UpdatePasswordDTO passwordDTO)
    
    Updates a user's password using a password reset token (hash ID).
    Used after forget password flow when user clicks reset link in email.
    Validates token, checks expiration, encodes new password, and clears reset token.
    
    Request Body:
        UpdatePasswordDTO containing userId, new password, and reset token (hashId)
    
    Business Logic:
        - Validates reset token (hashId) matches user record
        - Checks token has not expired
        - Validates new password meets requirements
        - Checks new password not in last 12 passwords
        - Encodes password with BCrypt
        - Updates user password
        - Clears reset token and expiration
        - Adds to password history
    
    Returns:
        Success response with confirmation message
    
    Raises:
        400: Invalid or expired token, password in history, validation failed
        404: User not found
    """
    try:
        result = await controller.userService.setPassword(X_tenantID, passwordDTO)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# ===== MISSING ENDPOINTS FROM JAVA USERCONTROLLER =====

@router.get("/workFlowUser")
async def getWorkFlowUsers(
    X_tenantID: str = Header(alias="X-tenantID"),
    sites: Optional[List[str]] = Query(None),
    sitedepartments: Optional[List[str]] = Query(None),
    contractId: Optional[str] = Query(None),
    userRoles: Optional[List[str]] = Query(None),
    userIds: Optional[List[str]] = Query(None),
    sortOrder: Optional[str] = Query("ASC"),
    controller: UserController = Depends(get_user_controller)
) -> List[User]:
    """
    Equivalent to Java: @GetMapping("/workFlowUser")
    public List<User> getWorkFlowUsers(...)
    
    Retrieves users for workflow assignment and approval processes.
    Filters by tenant, sites, departments, contracts, roles, and specific user IDs.
    Used in workflow engines to populate approver/assignee dropdowns.
    Results can be sorted by name in ascending or descending order.
    
    Query Parameters:
        sites: Optional - filter by site IDs
        sitedepartments: Optional - filter by department IDs
        contractId: Optional - filter by specific contract
        userRoles: Optional - filter by role names (converted to UserRoles enum)
        userIds: Optional - filter by specific user IDs
        sortOrder: Sort direction "ASC" or "DESC" (default: "ASC")
    
    Returns:
        List[User] objects sorted and filtered for workflow operations
    """
    try:
        # Convert string roles to UserRoles enum if needed
        userRoleEnums = []
        if userRoles:
            from app.models.valueobjects.UserRoles import UserRoles
            userRoleEnums = [UserRoles(role) for role in userRoles]
        
        return await controller.userService.getWorkFlowUsers(
            X_tenantID, sites or [], sitedepartments or [], contractId, 
            userRoleEnums, userIds or [], sortOrder
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{id}/notifyEntityUser")
async def notifyEntityUser(
    id: str = Path(alias="id"),
    X_Authorization: str = Header(alias="X-Authorization"),
    controller: UserController = Depends(get_user_controller)
):
    """
    Equivalent to Java: @GetMapping("/{id}/notifyEntityUser")
    public ResponseEntity<?> notifyEntityUser(@PathVariable("id") String userId)
    
    Sends a notification email to an entity user (client/customer organization user).
    Used to notify entity users about account creation, important updates,
    or required actions. Distinct from contractor/internal user notifications.
    
    Path Parameters:
        id: User ID of the entity user to notify
    
    Business Logic:
        - Validates user exists and is an entity user type
        - Retrieves user email and entity details
        - Sends templated notification email
        - Logs notification event
    
    Returns:
        Success response confirming notification sent
    
    Raises:
        404: User not found
        400: User is not entity type or email sending failed
    """
    try:
        await controller.userService.notifyEntityUser(id)
        return {"status": "success", "message": "Entity user notified successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/bulk")
async def updateUserList(
    userDTOList: List[UserDTO],
    X_Authorization: str = Header(alias="X-Authorization"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: UserController = Depends(get_user_controller)
) -> str:
    """
    Equivalent to Java: @PutMapping("/bulk")
    public ResponseEntity<String> updateUserList(@RequestBody List<UserDTO> userDTOList, @RequestHeader(value = "X-tenantID") String tenantId)
    
    Updates multiple users in a single batch operation.
    Validates each user, applies updates, and processes all changes transactionally.
    Used for bulk import/update operations from CSV, SCIM sync, or admin bulk edits.
    
    Request Body:
        List of UserDTO objects with updated user data
    
    Business Logic:
        - Validates each user exists in tenant
        - Converts DTOs to domain models
        - Validates no duplicate emails in batch
        - Updates users with proper validation
        - May process in transaction or individually based on implementation
    
    Returns:
        Success message: "User list updated successfully"
    
    Raises:
        400: Validation failed for one or more users
        404: One or more users not found
    """
    try:
        await controller.userService.updateUserList(userDTOList, X_tenantID)
        return "User list updated successfully"
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{id}/remindContractors")
async def remindContractors(
    id: str = Path(alias="id"),
    controller: UserController = Depends(get_user_controller)
):
    """
    Equivalent to Java: @GetMapping("/{id}/remindContractors")
    public ResponseEntity<?> remindContractors(@PathVariable("id") String userId)
    
    Sends reminder notifications to contractors associated with a specific user
    (typically a manager or site coordinator). Used for timesheet submissions,
    compliance document updates, or other contractor-specific reminders.
    
    Path Parameters:
        id: User ID (usually manager/coordinator who manages contractors)
    
    Business Logic:
        - Retrieves user and associated contractors
        - Filters contractors needing reminders (pending timesheets, documents, etc.)
        - Sends reminder emails to each contractor
        - Logs reminder events
    
    Returns:
        Success response confirming reminders sent
    
    Raises:
        404: User not found
        400: No contractors associated or email sending failed
    """
    try:
        await controller.userService.remindContractors(id)
        return {"status": "success", "message": "Contractor reminder sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/{id}/{action}")
async def blockOrDeactivateUser(
    id: str = Path(),
    action: BlockOrDeactivateAction = Path(description="Allowed actions: BLOCK, UNBLOCK, DEACTIVATE, REACTIVATE, DELETE"),
    X_Authorization: str = Header(alias="X-Authorization"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: UserController = Depends(get_user_controller)
) -> str:
    """
    Equivalent to Java: @PutMapping("/{id}/{action}")
    public ResponseEntity<String> blockOrDeactivateUser(...)
    
    Performs administrative actions on a user account: block, unblock, deactivate,
    reactivate, or delete. Validates action, updates user status, records action
    metadata (who performed action, timestamp), and may trigger notifications.
    
    Path Parameters:
        id: User ID to perform action on
        action: Action enum (BLOCK, UNBLOCK, DEACTIVATE, REACTIVATE, DELETE)
    
    Business Logic:
        - BLOCK: Temporarily blocks user access, sets isBlocked=true
        - UNBLOCK: Removes block, sets isBlocked=false
        - DEACTIVATE: Deactivates account, sets isActivated=false
        - REACTIVATE: Reactivates account, sets isActivated=true
        - DELETE: Soft delete, sets isDeleted=true
        - Records action metadata (actionBy from JWT, timestamp)
        - May send notification email to user
    
    Returns:
        Success message confirming action performed
    
    Raises:
        400: Invalid action or user already in target state
        404: User not found in tenant
        401: Unauthorized to perform action
    """
    try:
        result = await controller.userService.blockOrDeactivateUser(
            X_Authorization, X_tenantID, id, action
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{userId}/accessScope")
async def getUserAccessScope(
    userId: str = Path(alias="userId"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: UserController = Depends(get_user_controller)
) -> AccessScopeResponseDTO:
    """
    Equivalent to Java: @GetMapping("/{userId}/accessScope")
    public ResponseEntity<?> getUserAccessScope(@RequestHeader(value = "X-Authorization") String authorization, @RequestHeader(value = "X-tenantID") String tenantId, @PathVariable("userId") String userId)
    
    Retrieves the access scope (permissions, role-based access, site/department access) for a specific user.
    Returns what data and features the user can access based on their roles, tenant memberships,
    site assignments, and organizational hierarchy positions.
    
    Path Parameters:
        userId: User ID to get access scope for
    
    Business Logic:
        - Retrieves user from tenant
        - Collects all roles and permissions
        - Gathers site and department access
        - Determines contract access scopes
        - Builds comprehensive access matrix
        - Checks for surrogate access if applicable
    
    Returns:
        AccessScopeResponseDTO with:
        - roles: List of all roles assigned to the user
        - accessScopes: List of access scopes with regions, sites, and departments
    
    Example Response:
        {
            "roles": [
                {
                    "id": "62d8e1a2a18d662326f0ce07",
                    "roleName": "Contract Manager",
                    "roleDescription": "Contract Manager",
                    "roleType": "SYSTEM",
                    "rolePerformerTypes": ["CONTRACT_MANAGER"]
                }
            ],
            "accessScopes": [
                {
                    "role": { ... },
                    "allRegionsApplicable": false,
                    "regions": [
                        {
                            "id": "68d4cf14e793b580b9df70a5",
                            "regionName": { "regionName": "Smmc" },
                            "roles": [ ... ],
                            "allSitesApplicable": false,
                            "sites": [ ... ]
                        }
                    ]
                }
            ]
        }
    
    Raises:
        404: User not found in tenant
        401: Unauthorized to view user's access scope
    """
    try:
        result = await controller.userService.getUserAccessScope(X_tenantID, userId)
        
        # Transform the result to match AccessScopeResponseDTO structure
        if isinstance(result, dict):
            # Convert roles array
            roles = []
            if "roles" in result:
                for role in result["roles"]:
                    if isinstance(role, dict):
                        # Ensure required fields exist
                        role_dict = {
                            "id": role.get("id"),
                            "roleName": role.get("roleName"),
                            "roleDescription": role.get("roleDescription"),
                            "roleType": role.get("roleType", "SYSTEM"),
                            "rolePerformerTypes": role.get("rolePerformerTypes", [])
                        }
                        roles.append(role_dict)
                    elif isinstance(role, str):
                        # Fallback for string role names (backward compatibility)
                        roles.append({
                            "id": None,
                            "roleName": role,
                            "roleDescription": role,
                            "roleType": "SYSTEM",
                            "rolePerformerTypes": []
                        })
                    else:
                        # It's a Role object - convert to dict
                        if hasattr(role, 'model_dump'):
                            role_dict = role.model_dump()
                        elif hasattr(role, 'dict'):
                            role_dict = role.dict()
                        else:
                            role_dict = role.__dict__ if hasattr(role, '__dict__') else {}
                        
                        # Ensure required fields
                        roles.append({
                            "id": role_dict.get("id"),
                            "roleName": role_dict.get("roleName"),
                            "roleDescription": role_dict.get("roleDescription"),
                            "roleType": role_dict.get("roleType", "SYSTEM"),
                            "rolePerformerTypes": role_dict.get("rolePerformerTypes", [])
                        })
            
            # Get accessScopes from result - service now provides fully formed accessScopes
            access_scopes = result.get("accessScopes", [])
            
            # Build the proper response
            response_data = {
                "roles": roles,
                "accessScopes": access_scopes
            }
            
            return AccessScopeResponseDTO(**response_data)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/ssoid")
async def setSsoId(
    userSsoIdDTO: UserSsoIdDTO,
    controller: UserController = Depends(get_user_controller)
):
    """
    Equivalent to Java: @PostMapping("/ssoid")
    public ResponseEntity<?> setSsoId(@RequestBody UserSsoIdDTO userSsoIdDTO)
    
    Sets or updates the SSO (Single Sign-On) ID for a user.
    Maps the user's account to their corporate SSO identity for seamless login.
    Validates SSO ID uniqueness across the system and updates user record.
    
    Request Body:
        UserSsoIdDTO containing userId and new ssoId
    
    Business Logic:
        - Validates user exists
        - Checks SSO ID not already in use by another user
        - Updates user's ssoId field
        - May trigger SSO provider sync
        - Logs SSO ID change event
    
    Returns:
        Success response with updated user data
    
    Raises:
        400: SSO ID already in use, invalid format
        404: User not found
    """
    try:
        result = await controller.userService.setSsoId(userSsoIdDTO)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/inactiveUsers")
async def getInactiveUsers(
    X_tenantID: str = Header(alias="X-tenantID"),
    ssoIdAvailable: bool = Query(False),
    controller: UserController = Depends(get_user_controller)
) -> List[User]:
    """
    Equivalent to Java: @GetMapping("/inactiveUsers")
    public List<User> getInactiveUsers(@RequestHeader(value = "X-tenantID") String tenantId, @RequestParam("ssoIdAvailable") boolean ssoIdAvailable)
    
    Retrieves users who have not logged in recently (inactive accounts).
    Used for compliance reporting, account cleanup, or sending reactivation reminders.
    Can filter by whether users have SSO ID configured.
    
    Query Parameters:
        ssoIdAvailable: Filter by SSO ID presence (true=has SSO, false=no SSO, or all)
    
    Business Logic:
        - Identifies users with no recent login (e.g., >90 days)
        - Filters by tenant
        - Optionally filters by SSO ID presence/absence
        - Returns users needing attention or reactivation
    
    Returns:
        List[User] objects representing inactive user accounts
    """
    try:
        return await controller.userService.getInactiveUsers(X_tenantID, ssoIdAvailable)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/inactiveUsers/reminderToLogin")
async def remindInactiveUsersToLogin(
    userIds: List[str] = Query(alias="userIds"),
    controller: UserController = Depends(get_user_controller)
):
    """
    Equivalent to Java: @GetMapping("/inactiveUsers/reminderToLogin")
    public ResponseEntity<?> remindInactiveUsersToLogin(@RequestParam(value = "userIds", required = true) List<String> userIds)
    
    Sends reminder emails to inactive users encouraging them to log in.
    Used for user retention campaigns and reactivating dormant accounts.
    Sends bulk notifications to multiple users at once.
    
    Query Parameters:
        userIds: Required - list of user IDs to send reminders to
    
    Business Logic:
        - Validates all user IDs exist
        - Sends templated reminder email to each user
        - Includes login link and account benefits
        - Logs reminder events for tracking
    
    Returns:
        Success response confirming reminders sent
    
    Raises:
        400: Invalid user IDs or email sending failed
    """
    try:
        await controller.userService.remindInactiveUsersToLogin(userIds)
        return {"status": "success", "message": "Login reminders sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/inactiveUsers/reminderToSetSsoId")
async def remindInactiveUsersToSetSsoId(
    userIds: List[str] = Query(alias="userIds"),
    controller: UserController = Depends(get_user_controller)
):
    """
    Equivalent to Java: @GetMapping("/inactiveUsers/reminderToSetSsoId")
    public ResponseEntity<?> remindInactiveUsersToSetSsoId(@RequestParam(value = "userIds", required = true) List<String> userIds)
    
    Sends reminder emails to users who haven't configured their SSO ID.
    Encourages users to set up Single Sign-On for easier login.
    Used for SSO adoption campaigns and compliance requirements.
    
    Query Parameters:
        userIds: Required - list of user IDs missing SSO ID
    
    Business Logic:
        - Validates all user IDs exist
        - Checks users don't already have SSO ID
        - Sends templated reminder email with SSO setup instructions
        - Includes link to SSO configuration page
        - Logs reminder events
    
    Returns:
        Success response confirming reminders sent
    
    Raises:
        400: Invalid user IDs or email sending failed
    """
    try:
        await controller.userService.remindInactiveUsersToSetSsoId(userIds)
        return {"status": "success", "message": "SSO ID setup reminders sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/NonEntityAccessWorkflowUsers")
async def getNonEntityAccessWorkflowUsers(
    X_tenantID: str = Header(alias="X-tenantID"),
    X_Authorization: str = Header(alias="X-Authorization"),
    controller: UserController = Depends(get_user_controller)
) -> List[User]:
    """
    Equivalent to Java: @GetMapping("/NonEntityAccessWorkflowUsers")
    public List<User> getNonEntityAccessWorkflowUsers(@RequestHeader(value = "X-tenantID") String tenantId, @RequestHeader(value = "X-Authorization") String authorization)
    
    Retrieves users who participate in workflows but don't have entity-level access.
    These are typically internal users, contractors, or service providers who can
    be assigned workflow tasks but shouldn't access entity/client-level data.
    Used for populating workflow assignment dropdowns with appropriate users.
    
    Business Logic:
        - Filters users by tenant
        - Excludes users with entity access level
        - Includes users with workflow participation roles
        - May filter based on requesting user's permissions from JWT
        - Returns users suitable for workflow task assignment
    
    Returns:
        List[User] objects representing non-entity workflow participants
    """
    try:
        return await controller.userService.getNonEntityAccessWorkflowUsers(X_tenantID, X_Authorization)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/mySurrogate/{userId}")
async def getMySurrogate(
    userId: str = Path(alias="userId"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: UserController = Depends(get_user_controller)
) -> List[User]:
    """
    Equivalent to Java: @GetMapping("/mySurrogate/{userId}")
    
    Retrieves the list of surrogate users configured for a specific user.
    Surrogates are users who can act on behalf of another user during their absence.
    Used for vacation/leave delegation and workflow continuity.
    
    Path Parameters:
        userId: ID of the user whose surrogates to retrieve
    
    Business Logic:
        - Retrieves user from tenant
        - Fetches configured surrogate relationships
        - Checks active surrogate schedules (date ranges)
        - Returns list of users authorized to act as surrogates
    
    Returns:
        List[User] objects representing configured surrogate users
    
    Raises:
        404: User not found in tenant
    """
    try:
        return await controller.userService.getMySurrogate(X_tenantID, userId)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/scimGroup/usersUpdate")
async def updateScimGroupUsers(
    groupIds: List[str] = Query(alias="groupIds"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: UserController = Depends(get_user_controller)
):
    """
    Equivalent to Java: @GetMapping("/scimGroup/usersUpdate")
    public ResponseEntity<?> updateScimGroupUsers(@RequestParam(value = "groupIds", required = true) List<String> groupIds, @requestHeader(value = "X-tenantID") String tenantId)
    
    Synchronizes user memberships for SCIM groups. Updates user records based on
    group membership changes from SCIM provider (Azure AD, Okta, etc.).
    Adds/removes roles and permissions based on group assignments.
    Part of SCIM 2.0 protocol implementation for identity provisioning.
    
    Query Parameters:
        groupIds: Required - list of SCIM group IDs to sync
    
    Business Logic:
        - Retrieves SCIM group definitions from provider
        - Fetches current user memberships for each group
        - Compares with local user-role mappings
        - Adds users to groups (grants roles)
        - Removes users from groups (revokes roles)
        - Updates user records with new roles/permissions
        - Logs sync events for audit
    
    Returns:
        Success response with sync results
    
    Raises:
        400: Invalid group IDs or SCIM sync failed
        404: Groups not found
    """
    try:
        result = await controller.userService.updateScimGroupUsers(X_tenantID, groupIds)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/getUser")
async def getUsersForClient(
    X_Authorization: str = Header(alias="X-Authorization"),
    X_tenantID: str = Header(alias="X-tenantID"),
    titles: Optional[List[str]] = Query(None),
    controller: UserController = Depends(get_user_controller)
) -> List[User]:
    """
    Equivalent to Java: @GetMapping("/getUser")
    public List<User> getUsersForClient(@RequestHeader(value = "X-tenantID") String tenantId, @RequestParam(value = "titles", required = false) List<String> titles)
    
    Retrieves users for client/entity access, optionally filtered by job titles.
    Used in client-facing interfaces to show authorized users or contact lists.
    Filters by tenant and can narrow results by specific job titles.
    
    Query Parameters:
        titles: Optional - list of job titles to filter by (e.g., "Manager", "Supervisor")
    
    Business Logic:
        - Filters users by tenant
        - Optionally filters by job titles if provided
        - May include additional client-specific access checks
        - Returns users visible to client interface
    
    Returns:
        List[User] objects matching criteria
    
    Raises:
        404: No users found matching criteria
    """
    try:
        # Authorization header is accepted for parity with Java; not used in this handler currently
        return await controller.userService.getUsersForClient(X_tenantID, titles or [])
    except HTTPException as he:
        # Preserve service-level HTTP errors (e.g., 404) instead of converting to 400
        raise he
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/contracts/detach/{userId}/{contractId}")
async def detachContractsFromUser(
    userId: str = Path(alias="userId"),
    contractId: str = Path(alias="contractId"),
    controller: UserController = Depends(get_user_controller)
):
    """
    Equivalent to Java: @PutMapping("/contracts/detach/{userId}/{contractId}")
    public ResponseEntity<?> detachContractsFromUser(@PathVariable("userId") String userId, @PathVariable("contractId") String contractId)
    
    Removes a contract association from a user. Detaches the user from a specific
    contract, removing their access to contract-specific data and permissions.
    Used when a user completes a contract, transfers to different contract,
    or when contract access needs to be revoked.
    
    Path Parameters:
        userId: ID of the user to detach from contract
        contractId: ID of the contract to detach from user
    
    Business Logic:
        - Validates user exists
        - Validates contract exists in user's contracts list
        - Removes contract from user's contracts array
        - May revoke contract-specific roles/permissions
        - Updates user record
        - May trigger access recalculation
    
    Returns:
        Success response confirming detachment
    
    Raises:
        404: User not found or contract not associated with user
        400: Invalid user or contract ID
    """
    try:
        result = await controller.userService.detachContractsFromUser(userId, contractId)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# ===== FIX EXISTING ENDPOINTS TO USE CAMELCASE METHODS =====
# Note: The above endpoints are already fixed to use camelCase methods
# No additional duplicate endpoints needed

# Keep the dynamic single-segment route last to avoid shadowing static paths like '/metadata' or '/getUser'
@router.get("/{userId}")
async def getUserListById(
    userId: str = Path(alias="userId"),
    X_tenantID: str = Header(alias="X-tenantID"),
    controller: UserController = Depends(get_user_controller)
):
    """
    Equivalent to Java: @GetMapping("/{userId}")
    public User getUserListById(@RequestHeader(value = "X-tenantID") String tenantId, @PathVariable(name = "userId") String userId)
    
    Retrieves a single user by their ID within a specific tenant.
    Returns complete user profile including roles, sites, contracts, metadata, and access scope.
    This is the primary endpoint for fetching individual user details.
    
    IMPORTANT: This endpoint uses a dynamic path parameter and must be defined LAST
    in the router to avoid shadowing static paths like /metadata, /getUser, etc.
    
    Path Parameters:
        userId: ID of the user to retrieve
    
    Business Logic:
        - Validates user exists in specified tenant
        - Retrieves complete user record with all fields
        - Retrieves user's access scope (roles, regions, sites, departments)
        - Serializes with Pydantic aliasing (camelCase for API)
        - Returns full user profile with access scope
    
    Returns:
        User object with complete profile data including:
        - All user fields (firstName, lastName, email, etc.)
        - roles: List of assigned roles
        - sites: List of assigned sites
        - contracts: List of assigned contracts
        - accessScope: Hierarchical access structure with regions, sites, departments, and role-based permissions
    
    Example Response:
        {
            "id": "6424dea81a6c0d4b84d543a9",
            "firstName": "John",
            "lastName": "Doe",
            "email": "john@example.com",
            "roles": [...],
            "sites": [...],
            "accessScope": {
                "roles": [...],
                "allRegionsApplicable": false,
                "regions": [...]
            }
        }
    
    Raises:
        404: User not found in tenant
        400: Invalid user ID format
    """
    try:
        user = await controller.userService.getUserListById(X_tenantID, userId)
        user_dict = user.model_dump(by_alias=True, exclude_none=False)
        print(user_dict)
        # Flatten sites structure - extract sites array from sites.sites
        if "sites" in user_dict and isinstance(user_dict["sites"], dict) and "sites" in user_dict["sites"]:
            user_dict["sites"] = user_dict["sites"]["sites"]
        
        # Remove contracts field if it's null
        if "contracts" in user_dict and user_dict["contracts"] is None:
            del user_dict["contracts"]
        
        # Convert avgLoginSession to object structure with milliseconds
        if "avgLoginSession" in user_dict:
            # if isinstance(user_dict["avgLoginSession"], (int, float)):
            #     user_dict["avgLoginSession"] = {"milliseconds": user_dict["avgLoginSession"]}
            # elif isinstance(user_dict["avgLoginSession"], dict) and "milliseconds" not in user_dict["avgLoginSession"]:
            #     # If it's a dict but doesn't have milliseconds key, wrap it
            #     user_dict["avgLoginSession"] = {"milliseconds": user_dict["avgLoginSession"].get("millis", 0)}/
            user_dict["avgLoginSession"] = {"milliseconds": user_dict["avgLoginSession"] if isinstance(user_dict["avgLoginSession"], (int, float)) else 0}

        
        # Convert null id to empty string in title object
        if "title" in user_dict and isinstance(user_dict["title"], dict):
            if "id" in user_dict["title"] and user_dict["title"]["id"] is None:
                user_dict["title"]["id"] = ""
        
        # Ensure suffix object structure in name dict
        if "name" in user_dict and isinstance(user_dict["name"], dict):
            if "suffix" not in user_dict["name"]:
                user_dict["name"]["suffix"] = {"id": None, "suffix": None}
            elif not isinstance(user_dict["name"]["suffix"], dict):
                user_dict["name"]["suffix"] = {"id": None, "suffix": None}
        
        # Get access scope for the user
        try:
            access_scope_result = await controller.userService.getUserAccessScope(X_tenantID, userId)
            
            # Transform accessScope to match the response structure
            if isinstance(access_scope_result, dict):
                # Convert roles array
                roles = []
                if "roles" in access_scope_result:
                    for role in access_scope_result["roles"]:
                        if isinstance(role, dict):
                            role_dict = {
                                "id": role.get("id"),
                                "roleName": role.get("roleName"),
                                "roleDescription": role.get("roleDescription"),
                                "roleType": role.get("roleType", "SYSTEM"),
                                "rolePerformerTypes": role.get("rolePerformerTypes", [])
                            }
                            roles.append(role_dict)
                        elif isinstance(role, str):
                            roles.append({
                                "id": None,
                                "roleName": role,
                                "roleDescription": role,
                                "roleType": "SYSTEM",
                                "rolePerformerTypes": []
                            })
                        else:
                            if hasattr(role, 'model_dump'):
                                role_dict = role.model_dump()
                            elif hasattr(role, 'dict'):
                                role_dict = role.dict()
                            else:
                                role_dict = role.__dict__ if hasattr(role, '__dict__') else {}
                            
                            roles.append({
                                "id": role_dict.get("id"),
                                "roleName": role_dict.get("roleName"),
                                "roleDescription": role_dict.get("roleDescription"),
                                "roleType": role_dict.get("roleType", "SYSTEM"),
                                "rolePerformerTypes": role_dict.get("rolePerformerTypes", [])
                            })
                
                # Build accessScope structure
                access_scopes = access_scope_result.get("accessScopes", [])
                user_dict["accessScope"] = {
                    "roles": roles,
                    "allRegionsApplicable": False,
                    "regions": access_scopes if isinstance(access_scopes, list) else []
                }
        except Exception as e:
            # If access scope retrieval fails, provide empty structure
            print(f"Warning: Could not retrieve access scope for user {userId}: {str(e)}")
            user_dict["accessScope"] = {
                "roles": [],
                "allRegionsApplicable": False,
                "regions": []
            }
        
        return user_dict
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

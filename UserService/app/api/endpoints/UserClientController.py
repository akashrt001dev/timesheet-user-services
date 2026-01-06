import logging
from fastapi import APIRouter, Depends, status
from typing import List, Dict, Any, Optional
from app.models.valueobjects.ContractLite import ContractLite
from app.models.valueobjects.ContractStatus import ContractStatus
from app.models.aggregates.root.User import User
from app.repositories.UserRepository import UserRepository
from app.clients.EntityClient import EntityClient
from app.core.EmailNotification import EmailNotification
from app.core.constants import AppConstants as CONSTANTS

# Configure logger for this module
logger = logging.getLogger(__name__)

# Create router instance with prefix
router = APIRouter(prefix="/userClient")

# Email constants
EMAIL_SUBJECT = "WELCOME TO TIMESMART.AI"


async def get_dependencies_for_contract() -> tuple:
    """
    FastAPI dependency for required services.
    Equivalent to Spring Boot's @Autowired dependency injection.
    """
    from app.dependencies import get_user_repository, get_entity_client
    
    user_repository = await get_user_repository()
    entity_client = get_entity_client()
    
    return (user_repository, entity_client)


@router.post(
    "/contract/updateStatus",
    response_model=bool,
    status_code=status.HTTP_200_OK,
    summary="Trigger User Onboarding Emails for Contract Activation",
    description="Sends welcome/activation emails to uninvited users when contract is activated"
)
async def consume_contract(
    contract: ContractLite,
    dependencies: tuple = Depends(get_dependencies_for_contract)
) -> bool:
    """
    PRIMARY GOAL: Automatically send welcome/activation emails to newly added contract users.
    
    When a contract status changes to ACTIVE or ACTIVATION_READY, this endpoint:
    1. Identifies all uninvited users linked to the contract
    2. Fetches organization/entity details (name, subdomain, logo)
    3. Sends personalized welcome emails with activation links
    4. Marks users as "invited" in the database
    
    This initiates the user onboarding workflow.
    
    EQUIVALENT TO: Java UserClientController.consumeContract(@RequestBody ContractLite contract)
    
    Detailed Business Logic:
    ========================
    STEP 1: Validate Contract
      - Check contract is not null
      - Verify status is ACTIVE or ACTIVATION_READY (skip other statuses)
    
    STEP 2: Retrieve Users
      - Query database for all uninvited users linked to this contract
      - If no users found, return early (no action needed)
    
    STEP 3: Fetch Organization Details
      - Call EntityClient to get organization info for the tenant:
        * Organization name
        * Subdomain (for URL construction)
        * Logo URL (for email branding)
    
    STEP 4: For Each Uninvited User, Send Email and Update Status
      - Generate activation/login URL:
        * ACTIVE status → Domain login URL (e.g., https://acme.timesmart.ai)
        * ACTIVATION_READY → SSO activation URL with token (e.g., https://acme.timesmart.ai/sso/activate?token=UUID)
      
      - Build email template with variables:
        * fullName, firstName, lastName
        * userName (official email)
        * entityName (organization name)
        * setPasswordURL (activation link)
        * logo (organization logo URL)
        * roles (user's assigned roles)
      
      - Publish EmailDTO to RabbitMQ:
        * Queue: emailProducer-out-0
        * Template: contractorAccountActivation
        * Subject: "WELCOME TO TIMESMART.AI"
      
      - Update database:
        * Set user.isInvited = True
        * Persist to MongoDB
    
    STEP 5: Return Status
      - Return True if processing completed successfully
      - Return False if contract is null or fatal error occurs
    
    Use Case Example:
    =================
    When a healthcare facility activates a contract with TimeSmart:
    - All assigned staff members/service providers receive a welcome email
    - Email includes facility name and personalized activation link
    - Users can click link to set up their account
    - System marks them as invited to prevent duplicate emails
    
    Args:
        contract: ContractLite object containing:
            - id: Contract identifier (e.g., "contract-123")
            - contractName: Contract details with name (e.g., {"contractName": "Enterprise Contract"})
            - contractStatus: ACTIVE, DRAFT, EXPIRED, TERMINATED, or ACTIVATION_READY
            - tenant: Organization/entity reference (e.g., {"id": "tenant-456"})
            - contractDetail: Contract terms with dates
        
        dependencies: Tuple of (UserRepository, EntityClient)

    Returns:
        bool: True if contract processing completed successfully (or no action needed)
              False if contract is null or unexpected error occurs

    Example Request:
        POST /userClient/contract/updateStatus
        Content-Type: application/json
        
        {
            "id": "contract-123",
            "contractName": {"contractName": "Enterprise Contract"},
            "contractStatus": "ACTIVE",
            "tenant": {"id": "tenant-456"},
            "contractDetail": {
                "contractTerm": {
                    "startDate": "2024-01-01",
                    "endDate": "2024-12-31",
                    "effectiveDate": "2024-01-01",
                    "activationDate": "2024-01-05"
                }
            }
        }
        
    Example Response:
        true  (Email sending workflow initiated successfully)
    """
    try:
        user_repository, entity_client = dependencies
        email_notification = EmailNotification()
        
        # ==================== STEP 1: VALIDATE CONTRACT ====================
        if contract is not None:
            logger.info(f"Processing contract update for contract ID: {contract.id}")
            
            # Log contract details for debugging
            if contract.contractName:
                logger.debug(f"Contract Name: {contract.contractName.contractName}")
            if contract.contractStatus:
                logger.debug(f"Contract Status: {contract.contractStatus}")
            if contract.tenant:
                logger.debug(f"Tenant ID: {contract.tenant.id}")
            
            # Only process if status is ACTIVE or ACTIVATION_READY
            # Skip: DRAFT, EXPIRED, TERMINATED (no user onboarding for these)
            if contract.contractStatus not in [ContractStatus.ACTIVE, ContractStatus.ACTIVATION_READY]:
                logger.info(f"Skipping email sending for contract {contract.id} with status {contract.contractStatus}")
                return True
            
            # ==================== STEP 2: RETRIEVE UNINVITED USERS ====================
            # Query database: Find all users linked to this contract who are NOT yet invited
            logger.info(f"Retrieving uninvited users for contract: {contract.id}")
            users = await user_repository.getUnInvitedUsersByTenantIDandContract(contract.id)
            
            if not users:
                logger.info(f"No uninvited users found for contract: {contract.id}")
                return True
            
            logger.info(f"Found {len(users)} uninvited users for contract: {contract.id}")
            
            # ==================== STEP 3: FETCH ORGANIZATION DETAILS ====================
            # Get entity/organization info: name, subdomain, logo
            tenant_id = users[0].tenant.id if users[0].tenant else None
            if not tenant_id:
                logger.warning("No tenant ID found for users")
                return True
            
            logger.info(f"Fetching entity details for tenant: {tenant_id}")
            entity_dto = await entity_client.get_entity_by_id(tenant_id)
            
            if not entity_dto:
                logger.warning(f"No entity found for tenant ID: {tenant_id}")
                return True
            
            entity_name = entity_dto.entityName.entityName if entity_dto.entityName else "N/A"
            subdomain = entity_dto.subdomain or ""
            
            # Extract logo URL for email branding
            logo = ""
            if entity_dto.logo and hasattr(entity_dto.logo, 'file') and entity_dto.logo.file:
                logo = entity_dto.logo.file.fileURL or ""
            
            logger.info(f"Entity details - Name: {entity_name}, Subdomain: {subdomain}, Logo: {bool(logo)}")
            
            # ==================== STEP 4: SEND EMAILS TO EACH USER ====================
            # For each uninvited user:
            # - Generate activation/login URL
            # - Build email template with user + organization data
            # - Publish email to RabbitMQ
            # - Mark user as invited in database
            for user in users:
                await _send_email_and_update_is_invited(
                    user, entity_name, subdomain, logo, contract.contractStatus,
                    user_repository, email_notification
                )
            
            # ==================== STEP 5: RETURN STATUS ====================
            logger.info(f"Successfully processed contract update for ID: {contract.id}")
            return True
        else:
            logger.warning("Received null contract object")
            return False
            
    except Exception as exception:
        logger.error(f"Exception while processing contract: {str(exception)}", exc_info=True)
        return False


async def _send_email_and_update_is_invited(
    user: User, 
    entity_name: str, 
    subdomain: str, 
    logo: str, 
    contract_status: ContractStatus,
    user_repository: UserRepository,
    email_notification: EmailNotification
) -> None:
    """
    Send personalized welcome email to user and mark them as invited.
    
    This is the core onboarding mechanism:
    1. Generate activation/login URL based on contract status
    2. Build personalized email with user + organization data
    3. Publish email to RabbitMQ for delivery
    4. Update database to mark user as invited (prevents duplicate emails)

    Args:
        user: User to send email to
        entity_name: Organization name (for email branding)
        subdomain: Organization subdomain (for URL construction)
        logo: Organization logo URL (for email branding)
        contract_status: ACTIVE or ACTIVATION_READY
        user_repository: For updating user's isInvited flag
        email_notification: For publishing email to RabbitMQ
    """
    try:
        logger.info(f"Sending email to user: {user.id}")
        
        # Prepare email recipients
        to_address = [user.email.officialEmail] if user.email else []
        
        if not to_address:
            logger.warning(f"No email address found for user {user.id}")
            return
        
        # ========== BUILD PERSONALIZED EMAIL TEMPLATE ==========
        # Email variables sent to email service:
        # - User identification: fullName, firstName, lastName, userName (email)
        # - Organization branding: entityName, logo
        # - Activation link: setPasswordURL (generated based on status)
        # - User context: roles (their assigned roles in this contract)
        
        template_values: Dict[str, Any] = {
            "fullName": user.name.getFullName() if user.name else "User",
            "firstName": user.name.firstName if user.name else "",
            "lastName": user.name.lastName if user.name else "",
            "userName": user.email.officialEmail if user.email else "",
            "entityName": entity_name,
            "logo": logo,
        }
        
        # ========== GENERATE ACTIVATION/LOGIN URL ==========
        # URL type depends on contract status:
        # - ACTIVE: User logs in directly to organization domain
        #   Format: https://{subdomain}.timesmart.ai
        # - ACTIVATION_READY: User completes SSO setup with token
        #   Format: https://{subdomain}.timesmart.ai/sso/activate?token={UUID}
        
        redirect_url = ""
        if contract_status == ContractStatus.ACTIVE:
            redirect_url = _domain_url_creation(subdomain)
        elif contract_status == ContractStatus.ACTIVATION_READY:
            redirect_url = await _generate_sso_id_updation_url(user, subdomain)
        
        template_values["setPasswordURL"] = redirect_url
        
        # Add user roles if available
        if user.roles:
            template_values["roles"] = [role.roleName for role in user.roles]
        
        logger.debug(f"Email template values - To: {to_address}, Entity: {entity_name}")
        
        # ========== PUBLISH EMAIL TO RABBITMQ ==========
        # Email service details:
        # - Queue: emailProducer-out-0 (standard email queue)
        # - Template: contractorAccountActivation (welcome email template)
        # - Subject: "WELCOME TO TIMESMART.AI"
        # - Tenant: Used for multi-tenant email routing
        
        tenant_id = user.tenant.id if user.tenant else "default"
        success = email_notification.send_mail(
            producer_binding=CONSTANTS.PRODUCER_BINDING_NAME,
            to=to_address,
            subject=EMAIL_SUBJECT,
            template_value=template_values,
            template_name="contractorAccountActivation",
            tenant_id=tenant_id
        )
        
        if success:
            logger.info(f"Successfully sent email to: {to_address[0]}")
        else:
            logger.warning(f"Failed to send email to: {to_address[0]}")
        
        # ========== MARK USER AS INVITED ==========
        # Update database to set isInvited = True
        # This prevents duplicate welcome emails if contract is reactivated
        # Done regardless of email success to avoid retry loops
        
        user.isInvited = True
        await user_repository.save_user(user)
        logger.info(f"Updated isInvited flag for user: {user.id}")
        
    except Exception as e:
        logger.error(f"Exception in email sending for user {user.id}: {str(e)}", exc_info=True)


def _domain_url_creation(subdomain: str) -> str:
    """
    Creates domain URL from subdomain.
    Format: {protocol}{subdomain}.{appBaseURL}

    Args:
        subdomain: Subdomain to create URL for

    Returns:
        Full domain URL
    """
    try:
        protocol = getattr(CONSTANTS, 'PROTOCOL', 'https://')
        app_base_url = getattr(CONSTANTS, 'APP_BASE_URL', 'timesmart.ai')
        domain_url = f"{protocol}{subdomain}.{app_base_url}"
        logger.info(f"Generated domain URL: {domain_url}")
        return domain_url
    except Exception as e:
        logger.error(f"Exception in _domain_url_creation: {str(e)}")
        return ""


async def _generate_sso_id_updation_url(user: User, subdomain: str) -> str:
    """
    Generates SSO ID updation URL for activation-ready contracts.

    Args:
        user: User object
        subdomain: Subdomain for URL creation

    Returns:
        SSO updation URL
    """
    try:
        import uuid
        activation_id = str(uuid.uuid4())
        logger.info(f"Generated activation link ID: {activation_id} for user: {user.id}")
        
        # TODO: Save activation link ID in UserActivationLinkIdRepository
        sso_url = _sso_url_creation(activation_id, subdomain)
        logger.info(f"Generated SSO URL for user: {user.id}")
        return sso_url
    except Exception as e:
        logger.error(f"Exception in _generate_sso_id_updation_url: {str(e)}")
        return ""


def _sso_url_creation(activation_id: str, subdomain: str) -> str:
    """
    Creates SSO URL for account activation.

    Args:
        activation_id: UUID for activation
        subdomain: Subdomain for URL creation

    Returns:
        SSO activation URL
    """
    try:
        protocol = getattr(CONSTANTS, 'PROTOCOL', 'https://')
        app_base_url = getattr(CONSTANTS, 'APP_BASE_URL', 'timesmart.ai')
        sso_url = f"{protocol}{subdomain}.{app_base_url}/sso/activate?token={activation_id}"
        return sso_url
    except Exception as e:
        logger.error(f"Exception in _sso_url_creation: {str(e)}")
        return ""

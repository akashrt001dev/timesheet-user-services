# app/common/constants.py

class AppConstants:
    """
    Contains application-wide constants, migrated from CONSTANTS.java.
    """
    DAYS: int = 7
    
    PRODUCER_BINDING_NAME: str = "emailProducer-out-0"
    
    ACTIVITY_LOGGER: str = "Activity Logger"
    FINANCE_REVIEWER_APPROVER: str = "Finance Reviewer / Approver"
    FINANCE_USER: str = "Finance User"
    APPROVER: str = "Approver"
    REVIEWER: str = "Reviewer"
    AGGREGATOR: str = "Aggregator"
    ENTITY_SYS_ADMIN: str = "Entity Sys Admin"
    
    PAYMENT: str = "PAYMENT"
    REJECTED: str = "REJECTED"
    SUBMIT: str = "SUBMIT"
    REVIEWED: str = "REVIEWED"
    SINGLE: str = "SINGLE"
    MULTIPLE: str = "MULTIPLE"
    PAYMENT_COMPLETED: str = "PAYMENT_COMPLETED"
    
    USER_PRODUCER_BINDING_NAME: str = "userProducer-out-1"
    
    # URL configuration for domain and SSO URL creation
    PROTOCOL: str = "https://"
    APP_BASE_URL: str = "timesmart.ai"
    
    SCIM_PROXY: str = "proxy"
    DUMMY_USER_ID: str = "dummyuser@timesmartai.com"
    SCIM_ACTIVITY_LOGGER: str = "activitylogger"
    SCIM_APPROVER: str = "approver"
    SCIM_REVIEWER: str = "reviewer"
    SCIM_SYSTEM_ADMIN: str = "systemadmin"


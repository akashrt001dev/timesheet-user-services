from fastapi import FastAPI
from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.api.router import api_router
from app.core.rabbitmq_setup import setup_rabbitmq, shutdown_rabbitmq
from app.core.RabbitMQConfig import rabbitmq_config
from app.pubsub.EntityMessageConsumer import EntityMessageConsumer
from app.pubsub.TimesheetMessageConsumer import TimesheetMessageConsumer
from app.pubsub.EmailMessageSupplier import EmailMessageSupplier
import asyncio
import logging
from app.discovery.eureka_client import eureka_client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/openapi.json"
)

# Global consumer instances
entity_consumer = None
timesheet_consumer = None

async def startup_event():
    """
    Application startup event - initializes MongoDB and RabbitMQ
    Equivalent to Java Spring Boot @PostConstruct or @EventListener(ApplicationReadyEvent.class)
    """
    try:
        # Connect to MongoDB
        await connect_to_mongo()
        logger.info("MongoDB connection established")
        
        # Initialize controllers and services (MUST happen before RabbitMQ)
        await initialize_dependencies()
        logger.info("Dependencies initialized successfully")
        
        # Setup RabbitMQ exchanges and queues (non-blocking)
        try:
            await asyncio.wait_for(setup_rabbitmq(), timeout=10.0)
            logger.info("RabbitMQ setup completed")
            
            # Initialize and start message consumers (equivalent to Java @Bean consumers)
            await start_message_consumers()
            logger.info("Message consumers started")
        except asyncio.TimeoutError:
            logger.warning("RabbitMQ connection timed out - service will continue without message consumers")
        except Exception as rabbit_err:
            logger.warning(f"RabbitMQ setup failed: {rabbit_err} - service will continue without message consumers")
        
        # Register with Eureka and start heartbeat loop
        try:
            registered = await eureka_client.register()
            if registered:
                await eureka_client.start_heartbeat_loop()
            else:
                logger.warning("Eureka registration failed; service will continue without discovery")
        except Exception as eureka_err:
            logger.warning(f"Eureka registration failed: {eureka_err} - service will continue without discovery")
        
    except Exception as e:
        logger.error(f"Critical startup failure: {e}")
        raise

async def initialize_dependencies():
    """
    Initialize core dependencies (repositories, services, controllers)
    This MUST succeed for the application to work, regardless of RabbitMQ/Eureka status
    """
    from app.repositories.UserJobDetailsRepository import UserJobDetailsRepository
    from app.scheduler.UserJobScheduler import UserJobScheduler
    from app.db.mongodb import get_database
    from app.repositories.UserRepository import UserRepository
    from app.clients.EntityClient import EntityClient
    from app.services.UserService import UserService
    from app.repositories.GroupRepository import GroupRepository
    from app.repositories.RoleRepository import RoleRepository
    from app.repositories.ProfilePictureRepository import ProfilePictureRepository
    from app.repositories.SurrogateLogRepository import SurrogateLogRepository
    from app.repositories.UserActivationLinkIdRepository import UserActivationLinkIdRepository
    from app.repositories.UserPasswordRepository import UserPasswordRepository
    from app.repositories.UserSessionRepository import UserSessionRepository
    from app.clients.ContractClient import ContractClient
    from app.clients.TimesheetClient import TimesheetClient
    from app.core.QueryProcessor import QueryProcessor
    from app.security.JwtUtil import JwtUtil
    from app.security.OauthJwtDecoder import OauthJwtDecoder
    from app.services.RoleService import RoleService
    from app.pubsub.EmailMessageSupplier import EmailMessageSupplier
    from app.security.JwtUserDetailService import JwtUserDetailService
    from app.api.endpoints.UserController import get_user_controller
    
    db = get_database()
    
    # Initialize repositories
    user_repo = UserRepository(db)
    group_repo = GroupRepository(db)
    role_repo = RoleRepository(db)
    profile_pic_repo = ProfilePictureRepository(db)
    surrogate_log_repo = SurrogateLogRepository(db)
    user_activation_repo = UserActivationLinkIdRepository(db)
    user_password_repo = UserPasswordRepository(db)
    user_session_repo = UserSessionRepository(db)
    
    # Initialize clients
    entity_client = EntityClient()
    contract_client = ContractClient()
    timesheet_client = TimesheetClient()
    
    # Initialize email supplier
    email_supplier = EmailMessageSupplier()
    
    # Initialize additional components
    query_processor = QueryProcessor(db, user_repo)
    jwt_util = JwtUtil()
    oauth_jwt_decoder = OauthJwtDecoder()
    role_service = RoleService(role_repo)
    
    # Initialize UserService with all its dependencies
    user_service = UserService(
        userRepository=user_repo,
        profilePictureRepository=profile_pic_repo,
        queryProcessor=query_processor,
        contractClient=contract_client,
        entityClient=entity_client,
        jwtUtil=jwt_util,
        oauthJwtDecoder=oauth_jwt_decoder,
        timesheetClient=timesheet_client,
        userPasswordRepository=user_password_repo,
        userActivationLinkIdRepository=user_activation_repo,
        groupRepository=group_repo,
        roleService=role_service,
        emailMessageSupplier=email_supplier
    )
    
    # Initialize JwtUserDetailService
    jwt_user_detail_service = JwtUserDetailService(
        userRepository=user_repo,
        userSessionRepository=user_session_repo,
        jwtUtil=jwt_util
    )
    
    # Inject dependencies into controllers
    user_controller = get_user_controller()
    user_controller.userService = user_service
    user_controller.userRepository = user_repo
    user_controller.userDetailService = jwt_user_detail_service
    user_controller.jwtUtil = jwt_util
    
    logger.info("Core dependencies initialized successfully")

async def start_message_consumers():
    """Start all RabbitMQ message consumers and task scheduler"""
    try:
        # Set up RabbitMQ exchanges and queues
        await rabbitmq_config.declare_exchanges_and_queues()
        
        # Initialize task scheduler
        from app.repositories.UserJobDetailsRepository import UserJobDetailsRepository
        from app.scheduler.UserJobScheduler import UserJobScheduler
        from app.db.mongodb import get_database
        
        db = get_database()
        user_job_details_repo = UserJobDetailsRepository(db)
        job_scheduler = UserJobScheduler(user_job_details_repo)
        
        # Set up scheduler infrastructure
        await job_scheduler.setup_scheduler()
        
        # Start task consumer
        asyncio.create_task(job_scheduler.start_task_consumer())
        
        # Get already-initialized dependencies for consumers
        from app.repositories.UserRepository import UserRepository
        from app.clients.EntityClient import EntityClient
        from app.pubsub.EmailMessageSupplier import EmailMessageSupplier
        from app.api.endpoints.UserController import get_user_controller
        
        db = get_database()
        user_repo = UserRepository(db)
        entity_client = EntityClient()
        email_supplier = EmailMessageSupplier()
        
        # Get UserService from controller
        user_controller = get_user_controller()
        user_service = user_controller.userService
        
        # Start message consumers with proper dependencies
        from app.pubsub.EntityMessageConsumer import EntityMessageConsumer
        from app.pubsub.TimesheetMessageConsumer import TimesheetMessageConsumer
        
        global entity_consumer, timesheet_consumer
        entity_consumer = EntityMessageConsumer()
        timesheet_consumer = TimesheetMessageConsumer(
            emailMessageSupplier=email_supplier,
            userRepository=user_repo,
            entityClient=entity_client,
            userService=user_service
        )
        
        # Start consumers as background tasks
        asyncio.create_task(entity_consumer.start_consuming())
        asyncio.create_task(timesheet_consumer.start_consuming())
        
        logger.info("All RabbitMQ consumers and task scheduler started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start message consumers: {e}")
        raise

async def shutdown_event():
    """
    Application shutdown event - cleanup connections
    Equivalent to Java @PreDestroy or @EventListener(ContextClosedEvent.class)
    """
    try:
        # Stop message consumers
        if entity_consumer:
            await entity_consumer.close()
        if timesheet_consumer:
            await timesheet_consumer.close()
        logger.info("Message consumers stopped")
        
        # Shutdown RabbitMQ
        await shutdown_rabbitmq()
        logger.info("RabbitMQ connections closed")
        
        # Close MongoDB connection
        await close_mongo_connection()
        logger.info("MongoDB connection closed")

        # Deregister from Eureka
        try:
            await eureka_client.deregister()
        except Exception as _e:
            logger.warning("Error during Eureka deregistration: %s", _e)
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Register event handlers (equivalent to Java Spring lifecycle events)
app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}

@app.get("/health")
async def health():
    return {"status": "UP"}
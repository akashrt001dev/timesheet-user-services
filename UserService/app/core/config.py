from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "user-management-service"
    API_V1_STR: str = ""
    APP_SERVER_URL: str = "http://localhost:8001"
    
    # MongoDB Configuration
    MONGO_CONNECTION_STRING: str = "mongodb://localhost:27017/qa_timesmartai"
    MONGO_DATABASE: str = "qa_timesmartai"
    MONGO_HOST: str = "localhost"
    MONGO_PORT: int = 27017
    MONGO_USERNAME: str = "admin"
    MONGO_PASSWORD: str = "password"
    
    # JWT Configuration
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 3600  # 1 hour
    JWT_EXPIRATION_SECONDS: int = 3600  # 1 hour (alias for compatibility)
    JWT_REFRESH_EXPIRATION_SECONDS: int = 86400  # 24 hours
    
    # External service URLs
    ENTITY_CLIENT_URL: str = "http://localhost:8081"
    CONTRACT_CLIENT_URL: str = "http://localhost:8082"
    TIMESHEET_CLIENT_URL: str = "http://localhost:8083"
    
    # RabbitMQ Configuration
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USERNAME: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VIRTUAL_HOST: str = "/"
    RABBITMQ_CONNECTION_TIMEOUT: int = 30
    RABBITMQ_HEARTBEAT: int = 600
    
    # Application URLs and settings
    SSO_URL: str = "http://localhost:8080/auth"
    PROTOCOL: str = "http://"
    APP_BASE_URL: str = "localhost:3000"
    APP_CONTEXT: str = "/"
    
    # File server settings
    FILE_SERVER_PATH: str = "./uploads"
    FILE_SERVER_BASE_URL: str = "http://localhost:8000/static"
    
    # AWS S3 settings (optional)
    AWS_BUCKET_NAME: str = ""
    AWS_ACCESS_KEY: str = ""
    AWS_SECRET_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_BUCKET_URL: str = ""
    
    # Master entity
    MASTER_ENTITY_NAME: str = "master"

    # Eureka/Service Discovery settings
    EUREKA_SERVER_URL: str = "http://localhost:8761/eureka"
    SERVICE_NAME: str = "user-management-service"
    SERVER_HOST: str = "localhost"  # Set to the reachable hostname or IP for Eureka to call back
    SERVER_PORT: int = 8000  # Keep in sync with uvicorn run port
    EUREKA_HEARTBEAT_INTERVAL: int = 30  # seconds
    
    @property
    def RABBITMQ_URL(self) -> str:
        """Construct RabbitMQ connection URL"""
        return f"amqp://{self.RABBITMQ_USERNAME}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VIRTUAL_HOST}"
    
    class Config:
        env_file = ".env"
        populate_by_name = True
        validate_by_name = True  # Pydantic V2 name
        extra = "ignore"  # Ignore extra fields from .env

settings = Settings()
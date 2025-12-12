import asyncio
import logging
from app.core.RabbitMQConfig import rabbitmq_config
from app.pubsub.EntityMessageConsumer import EntityMessageConsumer
from app.pubsub.ContractMessageConsumer import ContractMessageConsumer
from app.pubsub.TimesheetMessageConsumer import TimesheetMessageConsumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_rabbitmq():
    """
    Setup RabbitMQ exchanges, queues, and start consumers
    """
    try:
        # Initialize RabbitMQ configuration
        await rabbitmq_config.declare_exchanges_and_queues()
        
        logger.info("RabbitMQ setup completed successfully")
        
        # Note: In a real application, you would also start your consumers here
        # Example:
        # entity_consumer = EntityMessageConsumer(...)
        # await entity_consumer.start_consuming()
        
    except Exception as e:
        logger.error(f"Failed to setup RabbitMQ: {e}")
        raise

async def shutdown_rabbitmq():
    """
    Gracefully shutdown RabbitMQ connections
    """
    try:
        await rabbitmq_config.close()
        logger.info("RabbitMQ connections closed")
    except Exception as e:
        logger.error(f"Error closing RabbitMQ connections: {e}")

if __name__ == "__main__":
    # For testing RabbitMQ setup
    asyncio.run(setup_rabbitmq())

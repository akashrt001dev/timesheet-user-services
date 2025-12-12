import logging
import json
from typing import Dict, Any
import aio_pika
from ..core.RabbitMQConfig import rabbitmq_config
from ..models.DTO.EntityDTO import EntityDTO

class EntityMessageConsumer:
    """
    RabbitMQ message consumer for entity-related events.
    Equivalent to Java @Bean Consumer<EntityDTO> pattern.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.queue_name = "entity_queue"
    
    async def entity_consumer(self, message: aio_pika.IncomingMessage):
        """
        Process entity messages (equivalent to Java Consumer<EntityDTO>)
        """
        try:
            async with message.process():
                # Parse message body
                message_data = json.loads(message.body.decode())
                self.logger.info(f"Received entity message: {message_data}")
                
                # Convert to EntityDTO
                entity_dto = EntityDTO(**message_data)
                
                # Process the entity message
                await self.process_entity_message(entity_dto)
                
        except Exception as e:
            self.logger.error(f"Error processing entity message: {str(e)}")
    
    async def process_entity_message(self, entity_dto: EntityDTO):
        """
        Process the entity DTO message
        """
        self.logger.info(f"Processing entity: {entity_dto.entityId}")
        
        # Add your entity processing logic here
        # This is where you would handle entity updates, creations, etc.
        
        # Example: Update user records when entity information changes
        # await self.update_users_for_entity(entity_dto)
    
    async def start_consuming(self):
        """
        Start consuming entity messages from RabbitMQ
        """
        try:
            await rabbitmq_config.connect()
            
            # Get the entity queue
            queue = await rabbitmq_config.channel.get_queue(self.queue_name)
            
            # Start consuming messages
            await queue.consume(self.entity_consumer)
            
            self.logger.info(f"Started consuming messages from queue: {self.queue_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to start entity message consumer: {str(e)}")
            raise

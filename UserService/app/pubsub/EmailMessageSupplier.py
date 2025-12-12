import asyncio
import json
import aio_pika
from aiormq.exceptions import ChannelPreconditionFailed
from typing import Callable
from app.models.DTO.EmailDTO import EmailDTO

class EmailMessageSupplier:
    """
    Python equivalent of Java EmailMessageSupplier
    Handles email message production functionality with RabbitMQ integration
    """
    
    def __init__(self, rabbitmq_url: str = "amqp://localhost/"):
        self.rabbitmq_url = rabbitmq_url
        self.connection = None
        self.channel = None
    
    async def connect(self):
        """
        Establish RabbitMQ connection
        """
        if not self.connection:
            self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self.channel = await self.connection.channel()
    
    async def close(self):
        """
        Close RabbitMQ connection
        """
        if self.connection:
            await self.connection.close()
    
    def emailProducer(self) -> Callable[[EmailDTO], EmailDTO]:
        """
        Equivalent to Java @Bean emailProducer() method
        Returns a function that processes EmailDTO objects
        """
        def process_email(emailDTO: EmailDTO) -> EmailDTO:
            # In Java this just returns the emailDTO as-is
            # This would typically integrate with a message broker like RabbitMQ/Kafka
            return emailDTO
        
        return process_email
    
    async def send_email(self, emailDTO: EmailDTO) -> EmailDTO:
        """
        Async method to send email messages via RabbitMQ
        Matches Java: streamBridge.send(CONSTANTS.PRODUCER_BINDING_NAME, emailDTO)
        """
        await self.connect()
        
        # Create or get direct exchange aligned with Java destination
        # QA: spring.cloud.stream.bindings.emailProducer-out-0.destination=emailProducer-out
        try:
            exchange = await self.channel.declare_exchange(
                "emailProducer-out",
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )
        except ChannelPreconditionFailed:
            exchange = await self.channel.get_exchange("emailProducer-out")
        
        # Publish email message with Java-compatible routing key
        message = aio_pika.Message(
            emailDTO.json().encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        
        # Use empty routing key for direct exchange
        await exchange.publish(
            message,
            routing_key=""
        )
        
        processor = self.emailProducer()
        return processor(emailDTO)
    
    async def send_user_update(self, binding_name: str, user_data: dict):
        """
        Send user update messages via RabbitMQ (used by SurrogateService)
        Matches Java: streamBridge.send(CONSTANTS.USER_PRODUCER_BINDING_NAME, user)
        """
        await self.connect()
        
        # Create or get direct exchange for user updates
        # QA: spring.cloud.stream.bindings.userProducer-out-1.destination=userProducer-out-1
        try:
            exchange = await self.channel.declare_exchange(
                "userProducer-out-1",
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )
        except ChannelPreconditionFailed:
            exchange = await self.channel.get_exchange("userProducer-out-1")
        
        # Publish user update message with Java-compatible routing key
        message = aio_pika.Message(
            json.dumps(user_data).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        
        # Use empty routing key for direct exchange
        await exchange.publish(
            message,
            routing_key=""
        )
        
        print(f"Published user update to RabbitMQ with Java-compatible routing key 'userProducer-out-1'")

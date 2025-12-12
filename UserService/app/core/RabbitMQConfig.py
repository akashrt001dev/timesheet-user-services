import asyncio
import aio_pika
from typing import Dict, Any
import logging
from .config import settings
from aiormq.exceptions import ChannelPreconditionFailed

class RabbitMQConfig:
    """
    RabbitMQ configuration and connection management
    """
    
    def __init__(self, rabbitmq_url: str = None):
        self.rabbitmq_url = rabbitmq_url or settings.RABBITMQ_URL
        self.connection = None
        self.channel = None
        self.LOG = logging.getLogger(__name__)
    
    async def connect(self):
        """
        Establish RabbitMQ connection
        """
        if not self.connection or self.connection.is_closed:
            try:
                self.connection = await aio_pika.connect_robust(
                    self.rabbitmq_url,
                    heartbeat=settings.RABBITMQ_HEARTBEAT,
                    client_properties={
                        "connection_name": f"{settings.PROJECT_NAME}-connection"
                    }
                )
                self.channel = await self.connection.channel()
                await self.channel.set_qos(prefetch_count=10)  # Process up to 10 messages concurrently
                self.LOG.info(f"Connected to RabbitMQ at {settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}")
            except Exception as e:
                self.LOG.error(f"Failed to connect to RabbitMQ: {e}")
                raise
    
    async def close(self):
        """
        Close RabbitMQ connection
        """
        if self.channel and not self.channel.is_closed:
            await self.channel.close()
            
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            
        self.LOG.info("Disconnected from RabbitMQ")
    
    async def declare_exchanges_and_queues(self):
        """
        Declare all necessary exchanges, queues, and bindings for the application
        Equivalent to Java Spring Cloud Stream binding configuration
        """
        await self.connect()

        async def _get_or_declare_exchange(name: str, preferred_type: aio_pika.exchange.ExchangeType):
            """Declare the exchange if missing, otherwise reuse existing regardless of type.
            Strategy:
            - Try to declare with the preferred type (idempotent if type matches).
            - If type differs, broker raises ChannelPreconditionFailed: just get a handle to the existing exchange.
            - If other errors occur, try to get a handle; re-raise if that also fails.
            This avoids passive gets on non-existent exchanges which can close the channel during later binds/publishes.
            """
            try:
                return await self.channel.declare_exchange(name, preferred_type, durable=True)
            except ChannelPreconditionFailed:
                # Exchange exists but with a different type; use the existing one.
                self.LOG.warning(f"Exchange '{name}' exists with a different type; using existing")
                return await self.channel.get_exchange(name)
            except Exception as e:
                self.LOG.debug(f"Declare exchange '{name}' failed with {e}; attempting to get existing handle")
                # Fallback: try to get a handle (works if it already exists)
                return await self.channel.get_exchange(name)

        # Exchanges aligned with QA properties
        email_exchange = await _get_or_declare_exchange("emailProducer-out", aio_pika.ExchangeType.TOPIC)
        user_exchange = await _get_or_declare_exchange("userProducer-out-1", aio_pika.ExchangeType.TOPIC)
        user_out0_exchange = await _get_or_declare_exchange("userProducer-out", aio_pika.ExchangeType.TOPIC)
        common_exchange = await _get_or_declare_exchange("commonProducer-out", aio_pika.ExchangeType.DIRECT)
        entity_exchange = await _get_or_declare_exchange("entityCreationProducer-out", aio_pika.ExchangeType.TOPIC)

        contract_exchanges = []
        for dest in [
            "contractProducer-out",
            "contractProducer-out-1",
            "contractProducer-out-2",
            "contractProducer-out-3",
            "contractProducer-out-4",
        ]:
            ex = await _get_or_declare_exchange(dest, aio_pika.ExchangeType.TOPIC)
            contract_exchanges.append(ex)

        activity_exchange = await _get_or_declare_exchange("activityProducer-out", aio_pika.ExchangeType.TOPIC)
        schedule_report_exchange = await _get_or_declare_exchange("scheduleReportEmailProducer-out", aio_pika.ExchangeType.TOPIC)
        error_exchange = await _get_or_declare_exchange("error_exchange", aio_pika.ExchangeType.TOPIC)

        # Queues and bindings
        queue_bindings = [
            {"queue": "email_queue", "exchange": email_exchange, "routing_keys": ["#"]},
            {"queue": "user_updates_queue", "exchange": user_exchange, "routing_keys": ["#"]},
            {"queue": "user_updates_queue", "exchange": user_out0_exchange, "routing_keys": ["#"]},
            {"queue": "entity_queue", "exchange": entity_exchange, "routing_keys": ["#"]},
            *[{"queue": "contract_queue", "exchange": ex, "routing_keys": ["#"]} for ex in contract_exchanges],
            {"queue": "timesheet_activity_queue", "exchange": activity_exchange, "routing_keys": ["#"]},
            {"queue": "timesheet_schedule_queue", "exchange": schedule_report_exchange, "routing_keys": ["#"]},
            {"queue": "error_queue", "exchange": error_exchange, "routing_keys": ["#"]},
        ]

        for binding in queue_bindings:
            queue = await self.channel.declare_queue(binding["queue"], durable=True)
            for routing_key in binding["routing_keys"]:
                await queue.bind(binding["exchange"], routing_key)
                self.LOG.info(
                    f"Bound queue '{binding['queue']}' to exchange '{binding['exchange'].name}' with routing key '{routing_key}'"
                )

        self.LOG.info("Declared all RabbitMQ exchanges, queues, and bindings")
    
    async def publish_message(self, exchange_name: str, routing_key: str, message_data: Dict[str, Any]):
        """
        Publish a message to RabbitMQ
        """
        await self.connect()
        
        # Ensure the exchange exists before publishing; prefer TOPIC when unknown.
        try:
            exchange = await self.channel.declare_exchange(exchange_name, aio_pika.ExchangeType.TOPIC, durable=True)
        except ChannelPreconditionFailed:
            # Exists with different type; just get a handle
            exchange = await self.channel.get_exchange(exchange_name)
        
        message = aio_pika.Message(
            str(message_data).encode() if isinstance(message_data, dict) else message_data.encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        
        await exchange.publish(message, routing_key=routing_key)
        self.LOG.info(f"Published message to {exchange_name} with routing key {routing_key}")

# Global RabbitMQ configuration instance
rabbitmq_config = RabbitMQConfig()

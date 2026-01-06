import json
import pika
import logging
from typing import List, Dict, Any, Optional

# Import the Pydantic DTO to structure the email message
from app.models.DTO.EmailDTO import EmailDTO
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global connection pool (reuse connections)
_rabbitmq_connection = None
_rabbitmq_channel = None


def _get_rabbitmq_connection():
    """Get or create RabbitMQ connection."""
    global _rabbitmq_connection, _rabbitmq_channel
    
    try:
        if _rabbitmq_connection is None or _rabbitmq_connection.is_closed:
            rabbitmq_host = getattr(settings, 'RABBITMQ_HOST', 'localhost')
            rabbitmq_port = getattr(settings, 'RABBITMQ_PORT', 5672)
            rabbitmq_user = getattr(settings, 'RABBITMQ_USER', 'guest')
            rabbitmq_password = getattr(settings, 'RABBITMQ_PASSWORD', 'guest')
            
            credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
            parameters = pika.ConnectionParameters(
                host=rabbitmq_host,
                port=rabbitmq_port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
                connection_attempts=3,
                retry_delay=2
            )
            
            _rabbitmq_connection = pika.BlockingConnection(parameters)
            _rabbitmq_channel = _rabbitmq_connection.channel()
            logger.info(f"Successfully connected to RabbitMQ at {rabbitmq_host}:{rabbitmq_port}")
    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        _rabbitmq_connection = None
        _rabbitmq_channel = None
        raise
    
    return _rabbitmq_connection, _rabbitmq_channel


class EmailNotification:
    """
    Handles sending email notifications by publishing messages to a RabbitMQ queue.
    Migrated from EmailNotification.java.
    
    Uses persistent connections with retry logic for reliability.
    """
    
    def __init__(self):
        """Initialize the EmailNotification service."""
        self.LOG = logger

    def send_mail(
        self,
        producer_binding: str,
        to: List[str],
        subject: str,
        template_value: Dict[str, Any],
        template_name: str,
        tenant_id: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Constructs an EmailDTO and sends it to a specified RabbitMQ queue.

        Args:
            producer_binding (str): The name of the RabbitMQ queue (destination).
            to (List[str]): A list of recipient email addresses.
            subject (str): The subject of the email.
            template_value (Dict[str, Any]): Data for the email template.
            template_name (str): The name of the email template to use.
            tenant_id (str): The ID of the tenant this email belongs to.
            cc (Optional[List[str]]): A list of CC recipient email addresses.
            bcc (Optional[List[str]]): A list of BCC recipient email addresses.

        Returns:
            bool: True if message was successfully published, False otherwise.
        """
        try:
            # Validate required parameters
            if not to or not producer_binding or not template_name:
                self.LOG.error("Missing required parameters for email sending")
                return False
            
            # Create Pydantic DTO with validated data
            email_dto = EmailDTO(
                to=to,
                subject=subject,
                templateValue=template_value or {},
                cc=cc or [],
                bcc=bcc or [],
                templateName=template_name,
                tenantId=tenant_id,
            )

            # Get RabbitMQ connection
            connection, channel = _get_rabbitmq_connection()
            
            # Declare the queue to ensure it exists
            channel.queue_declare(queue=producer_binding, durable=True)

            # Publish the message using Pydantic v2 compatible method
            message_body = email_dto.model_dump_json().encode('utf-8')
            
            channel.basic_publish(
                exchange='',
                routing_key=producer_binding,
                body=message_body,
                properties=pika.BasicProperties(
                    content_type='application/json',
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,  # Make message persistent
                    headers={'tenant_id': tenant_id}
                )
            )
            
            self.LOG.info(
                f"Successfully published email to queue '{producer_binding}' "
                f"for tenant '{tenant_id}' with recipients: {to}"
            )
            return True

        except Exception as e:
            self.LOG.error(
                f"Failed to send email notification to queue '{producer_binding}': {str(e)}",
                exc_info=True
            )
            # Reset connection on error to force reconnection next time
            global _rabbitmq_connection, _rabbitmq_channel
            _rabbitmq_connection = None
            _rabbitmq_channel = None
            return False


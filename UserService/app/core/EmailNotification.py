# app/common/email_notification.py

import json
import pika
import logging
from typing import List, Dict, Any, Optional

# Import the Pydantic DTO to structure the email message
from app.models.DTO.EmailDTO import EmailDTO

class EmailNotification:
    """
    Handles sending email notifications by publishing messages to a RabbitMQ queue.
    Migrated from EmailNotification.java.
    """
    def __init__(self, rabbitmq_host: str = 'localhost'):
        """
        Initializes the EmailNotification service.

        Args:
            rabbitmq_host: The hostname or IP address of the RabbitMQ server.
        """
        self.rabbitmq_host = rabbitmq_host
        self.connection = None
        self.channel = None
        self.LOG = logging.getLogger(__name__)

    def _connect(self):
        """Establishes a connection and channel to RabbitMQ."""
        if not self.connection or self.connection.is_closed:
            try:
                self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.rabbitmq_host))
                self.channel = self.connection.channel()
                self.LOG.info("Successfully connected to RabbitMQ for email notifications.")
            except pika.exceptions.AMQPConnectionError as e:
                self.LOG.error(f"Failed to connect to RabbitMQ: {e}")
                raise

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
    ):
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
        """
        try:
            self._connect()
            
            # Use the Pydantic model to create a structured and validated DTO
            email_dto = EmailDTO(
                to=to,
                subject=subject,
                templateValue=template_value,
                cc=cc or [],
                bcc=bcc or [],
                templateName=template_name,
                tenantId=tenant_id,
            )

            # Declare the queue to ensure it exists
            self.channel.queue_declare(queue=producer_binding, durable=True)

            # Publish the message, converting the Pydantic model to a JSON string
            self.channel.basic_publish(
                exchange='',
                routing_key=producer_binding,
                body=email_dto.json().encode('utf-8'), # Use Pydantic's built-in JSON export
                properties=pika.BasicProperties(
                    content_type='application/json',
                    delivery_mode=2,  # Make message persistent
                )
            )
            self.LOG.info(f"Successfully sent email notification task to queue '{producer_binding}'.")

        except Exception as e:
            self.LOG.error(f"Failed to send email notification: {e}")
        finally:
            if self.connection and self.connection.is_open:
                self.connection.close()


import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional, Dict, Any
import aio_pika
from ..core.RabbitMQConfig import rabbitmq_config
from ..repositories.UserJobDetailsRepository import UserJobDetailsRepository
from ..models.valueobjects.UserJobDetails import UserJobDetails, SurrogateJobDetails
from ..models.valueobjects.JobState import JobState

if TYPE_CHECKING:
    from ..models.aggregates.root.User import User
    from ..models.entity.SurrogateLog import SurrogateLog
    from ..models.valueobjects.SurrogateSchedule import SurrogateSchedule

class RabbitMQTaskScheduler:
    """
    RabbitMQ-based task scheduler to replace Celery.
    Uses RabbitMQ delayed message exchange for scheduling tasks.
    """
    
    def __init__(self, user_job_details_repo: UserJobDetailsRepository):
        self.user_job_details_repo = user_job_details_repo
        self.logger = logging.getLogger(self.__class__.__name__)
        self.scheduler_exchange = "scheduler_exchange"
        self.delayed_queue = "delayed_tasks_queue"
    
    async def setup_scheduler_infrastructure(self):
        """
        Set up RabbitMQ infrastructure for delayed tasks
        """
        await rabbitmq_config.connect()
        
        # Declare scheduler exchange
        scheduler_exchange = await rabbitmq_config.channel.declare_exchange(
            self.scheduler_exchange,
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        
        # Declare delayed tasks queue with TTL and dead letter exchange
        delayed_queue = await rabbitmq_config.channel.declare_queue(
            self.delayed_queue,
            durable=True,
            arguments={
                "x-message-ttl": 86400000,  # 24 hours default TTL
                "x-dead-letter-exchange": "task_execution_exchange",
                "x-dead-letter-routing-key": "execute.task"
            }
        )
        
        # Bind queue to exchange
        await delayed_queue.bind(scheduler_exchange, "schedule.*")
        
        # Declare task execution exchange
        execution_exchange = await rabbitmq_config.channel.declare_exchange(
            "task_execution_exchange",
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        
        # Declare task execution queue
        execution_queue = await rabbitmq_config.channel.declare_queue(
            "task_execution_queue",
            durable=True
        )
        
        await execution_queue.bind(execution_exchange, "execute.*")
        
        self.logger.info("RabbitMQ scheduler infrastructure set up successfully")
    
    async def schedule_delayed_task(
        self, 
        task_name: str, 
        task_data: Dict[str, Any], 
        execute_at: datetime
    ) -> str:
        """
        Schedule a task to execute at a specific time
        """
        await rabbitmq_config.connect()
        
        # Calculate delay in milliseconds
        delay_ms = int((execute_at - datetime.now()).total_seconds() * 1000)
        
        if delay_ms <= 0:
            # Execute immediately if time has passed
            await self.execute_task_immediately(task_name, task_data)
            return "immediate_execution"
        
        # Create task message
        task_message = {
            "task_name": task_name,
            "task_data": task_data,
            "scheduled_for": execute_at.isoformat(),
            "created_at": datetime.now().isoformat()
        }
        
        # Generate unique task ID
        import uuid
        task_id = str(uuid.uuid4())
        task_message["task_id"] = task_id
        
        # Publish message with TTL equal to delay
        exchange = await rabbitmq_config.channel.get_exchange(self.scheduler_exchange)
        
        message = aio_pika.Message(
            json.dumps(task_message).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            expiration=delay_ms,  # Message will expire and go to dead letter exchange
            headers={"task_id": task_id, "task_name": task_name}
        )
        
        await exchange.publish(message, routing_key="schedule.delayed_task")
        
        self.logger.info(f"Scheduled task {task_name} with ID {task_id} to execute at {execute_at}")
        return task_id
    
    async def execute_task_immediately(self, task_name: str, task_data: Dict[str, Any]):
        """
        Execute a task immediately
        """
        if task_name == "scheduled_surrogate_removal_job":
            await self.execute_surrogate_removal_job(task_data)
        else:
            self.logger.warning(f"Unknown task type: {task_name}")
    
    async def execute_surrogate_removal_job(self, task_data: Dict[str, Any]):
        """
        Execute surrogate removal job (equivalent to Celery task)
        """
        surrogate_id = task_data.get("surrogate_id")
        user_id = task_data.get("user_id")
        user_name = task_data.get("user_name")
        
        self.logger.info(f"Executing surrogate removal job for user: {user_name} ({user_id}), surrogate log ID: {surrogate_id}")
        
        try:
            from ..db.mongodb import get_database
            from ..repositories.UserRepository import UserRepository
            
            db = get_database()
            user_repo = UserRepository(db)
            
            user = await user_repo.find_by_id(user_id)
            if not user:
                self.logger.error(f"User with ID {user_id} not found.")
                return
            
            # Filter out the surrogate schedule entry to be removed
            original_count = len(user.surrogateSchedule) if hasattr(user, 'surrogateSchedule') else 0
            if hasattr(user, 'surrogateSchedule'):
                user.surrogateSchedule = [s for s in user.surrogateSchedule if s.surrogateLogId != surrogate_id]
            
            current_count = len(user.surrogateSchedule) if hasattr(user, 'surrogateSchedule') else 0
            
            if current_count < original_count:
                await user_repo.save(user)
                self.logger.info(f"Successfully removed surrogate schedule {surrogate_id} for user {user_id}.")
            else:
                self.logger.warning(f"Surrogate schedule {surrogate_id} not found on user {user_id}.")
                
        except Exception as e:
            self.logger.error(f"Error executing surrogate removal job: {str(e)}")
    
    async def schedule_surrogate_removal_job(
        self,
        surrogate_schedule: 'SurrogateSchedule',
        surrogate_user: 'User',
        surrogate_log_id: str
    ) -> str:
        """
        Schedule a surrogate removal job to run at a specific time.
        Replaces Celery-based scheduling.
        """
        task_data = {
            "surrogate_id": surrogate_schedule.surrogateLogId,
            "user_id": surrogate_user.id,
            "user_name": surrogate_user.name.getFullName() if surrogate_user.name else "Unknown"
        }
        
        # Schedule the task using RabbitMQ
        task_id = await self.schedule_delayed_task(
            "scheduled_surrogate_removal_job",
            task_data,
            surrogate_schedule.endDate
        )
        
        # Create and save the job details for tracking
        surrogate_job_details = SurrogateJobDetails(
            jobId=task_id,
            jobState=JobState.CREATED,
            surrogateLogId=surrogate_log_id
        )
        
        user_job_details = await self.user_job_details_repo.find_by_id(surrogate_user.id)
        if not user_job_details:
            user_job_details = UserJobDetails(id=surrogate_user.id, surrogateJobDetails=[])
        
        user_job_details.surrogateJobDetails.append(surrogate_job_details)
        await self.user_job_details_repo.save(user_job_details)
        
        return task_id
    
    async def delete_surrogate_job(self, surrogate_log: 'SurrogateLog'):
        """
        Cancel a previously scheduled surrogate removal job.
        Since RabbitMQ doesn't allow message cancellation after publishing,
        we mark the job as deleted and the consumer will ignore it.
        """
        user_job_details = await self.user_job_details_repo.get_user_job_details_by_surrogate_log_id(surrogate_log.id)
        
        if not user_job_details:
            return
        
        job_found_and_updated = False
        for job_detail in user_job_details.surrogateJobDetails:
            if job_detail.surrogateLogId == surrogate_log.id:
                # Mark job as deleted (consumer will check this status)
                job_detail.jobState = JobState.DELETED
                job_found_and_updated = True
                break
        
        if job_found_and_updated:
            await self.user_job_details_repo.save(user_job_details)
            self.logger.info(f"Marked surrogate job {surrogate_log.id} as deleted")
    
    async def start_task_consumer(self):
        """
        Start consuming and executing scheduled tasks
        """
        await rabbitmq_config.connect()
        
        execution_queue = await rabbitmq_config.channel.get_queue("task_execution_queue")
        
        async def process_task(message: aio_pika.IncomingMessage):
            try:
                async with message.process():
                    task_data = json.loads(message.body.decode())
                    task_id = task_data.get("task_id")
                    task_name = task_data.get("task_name")
                    
                    # Check if job was deleted before execution
                    if task_name == "scheduled_surrogate_removal_job":
                        surrogate_id = task_data["task_data"].get("surrogate_id")
                        if await self.is_job_deleted(surrogate_id):
                            self.logger.info(f"Skipping deleted job {task_id}")
                            return
                    
                    await self.execute_task_immediately(task_name, task_data["task_data"])
                    
            except Exception as e:
                self.logger.error(f"Error processing scheduled task: {str(e)}")
        
        await execution_queue.consume(process_task)
        self.logger.info("Started RabbitMQ task consumer")
    
    async def is_job_deleted(self, surrogate_log_id: str) -> bool:
        """
        Check if a job has been marked as deleted
        """
        try:
            user_job_details = await self.user_job_details_repo.get_user_job_details_by_surrogate_log_id(surrogate_log_id)
            if user_job_details:
                for job_detail in user_job_details.surrogateJobDetails:
                    if (job_detail.surrogateLogId == surrogate_log_id and 
                        job_detail.jobState == JobState.DELETED):
                        return True
            return False
        except Exception as e:
            self.logger.error(f"Error checking job deletion status: {str(e)}")
            return False

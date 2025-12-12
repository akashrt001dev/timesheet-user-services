from typing import TYPE_CHECKING
from .RabbitMQTaskScheduler import RabbitMQTaskScheduler
from ..repositories.UserJobDetailsRepository import UserJobDetailsRepository

if TYPE_CHECKING:
    from ..models.aggregates.root.User import User
    from ..models.entity.SurrogateLog import SurrogateLog
    from ..models.valueobjects.SurrogateSchedule import SurrogateSchedule

class UserJobScheduler:
    """
    Handles scheduling and deleting background jobs using RabbitMQ.
    Equivalent to the Java UserJobScheduler class.
    Replaces Celery with RabbitMQ-based task scheduling.
    """
    def __init__(self, user_job_details_repo: UserJobDetailsRepository):
        self.user_job_details_repo = user_job_details_repo
        self.task_scheduler = RabbitMQTaskScheduler(user_job_details_repo)

    async def schedule_surrogate_removal_job(
        self,
        surrogate_schedule: 'SurrogateSchedule',
        surrogate_user: 'User',
        surrogate_log_id: str
    ) -> str:
        """
        Schedules a surrogate removal job to run at a specific time using RabbitMQ.
        
        Returns:
            The task ID for the scheduled job.
        """
        return await self.task_scheduler.schedule_surrogate_removal_job(
            surrogate_schedule, surrogate_user, surrogate_log_id
        )

    async def delete_surrogate_job(self, surrogate_log: 'SurrogateLog'):
        """
        Deletes/cancels a previously scheduled surrogate removal job.
        """
        await self.task_scheduler.delete_surrogate_job(surrogate_log)
    
    async def setup_scheduler(self):
        """
        Set up the RabbitMQ scheduler infrastructure
        """
        await self.task_scheduler.setup_scheduler_infrastructure()
    
    async def start_task_consumer(self):
        """
        Start the task consumer for executing scheduled tasks
        """
        await self.task_scheduler.start_task_consumer()
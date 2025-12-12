from pydantic import BaseModel, Field
from typing import Optional, Any
from .JobState import JobState

class SurrogateJobDetails(BaseModel):
    jobId: Optional[Any] = None # JobId from org.jobrunr.jobs.JobId might not have a direct equivalent
    surrogateLogId: Optional[str] = None
    jobState: Optional[JobState] = None

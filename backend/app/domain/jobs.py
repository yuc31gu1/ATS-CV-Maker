from datetime import datetime

from pydantic import BaseModel, Field

JOB_TYPE_ANALYZE = "ANALYZE"
JOB_TYPE_TAILOR = "TAILOR"

JOB_STATUS_PENDING = "PENDING"
JOB_STATUS_RUNNING = "RUNNING"
JOB_STATUS_SUCCEEDED = "SUCCEEDED"
JOB_STATUS_FAILED = "FAILED"


class Job(BaseModel):
    id: str
    type: str
    status: str
    payload: dict = Field(default_factory=dict)
    result: dict | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
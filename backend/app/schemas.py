from enum import Enum

from pydantic import BaseModel


class DatabaseStatus(str, Enum):
    ok = "ok"
    unavailable = "unavailable"


class HealthDatabase(BaseModel):
    status: DatabaseStatus


class HealthResponse(BaseModel):
    status: str
    service: str
    database: HealthDatabase
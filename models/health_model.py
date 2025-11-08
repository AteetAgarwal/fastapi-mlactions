from typing import Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    message: str
    services: Optional[dict] = None
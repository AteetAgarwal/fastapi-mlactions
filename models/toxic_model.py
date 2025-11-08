from typing import Optional
from pydantic import BaseModel

class Query(BaseModel):
    text: str

class ToxicApiResponse(BaseModel):
    input: str
    is_flagged: bool
    model_label: Optional[str] = None
    score: Optional[float] = None

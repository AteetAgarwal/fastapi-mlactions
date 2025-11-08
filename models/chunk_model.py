from typing import List, Optional
from pydantic import BaseModel


class ChunkRequest(BaseModel):
    text: str
    chunk_token_limit: Optional[int] = 200
    overlap_tokens: Optional[int] = 50

class ChunkResponse(BaseModel):
    status: str
    message: str
    chunks: List[str]
    total_chunks: int
    total_tokens: int

class ChunkApiRequest(BaseModel):
    id: str
    index_name: str
    input_field_name: str = "body_content"
    output_field_name: str = "body_content_embeddings"
    force_update: bool = False
    chunk_token_limit: Optional[int] = 200
    overlap_tokens: Optional[int] = 50

class ChunkApiResponse(BaseModel):
    status: str
    message: str
    elasticsearch_indexed: bool = False
    document_id: Optional[str] = None
    action_performed: Optional[str] = None  # "created", "updated", "exists"

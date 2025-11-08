from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List, Optional
import logging
from models import (ChunkRequest, ChunkResponse, ChunkApiRequest, ChunkApiResponse)

# Import services
from services.chunking import SmartChunker
from services.elasticsearch import elasticsearch_service

logger = logging.getLogger(__name__)

chunking_router = APIRouter(tags=["chunking"])

def _chunk_text(request: ChunkRequest) -> ChunkResponse:
    """
    Private function to chunk text content using SmartChunker
    
    Args:
        request: ChunkRequest object containing text and chunking parameters
        
    Returns:
        ChunkResponse object containing chunking results
    """
    logger.info(f"Chunking text of length: {len(request.text)} characters")
    
    # Validate input
    if not request.text or not request.text.strip():
        raise ValueError("Text content cannot be empty")
    
    # Create chunker with specified parameters
    chunker = SmartChunker(
        chunk_token_limit=request.chunk_token_limit,
        overlap_tokens=request.overlap_tokens
    )
    
    # Split text into chunks
    chunks = chunker.split(request.text)
    
    # Calculate total tokens
    from services.chunking import num_tokens
    total_tokens = sum(num_tokens(chunk) for chunk in chunks)
    
    logger.info(f"Successfully chunked text into {len(chunks)} chunks with {total_tokens} total tokens")
    
    return ChunkResponse(
        status="success",
        message=f"Text successfully chunked into {len(chunks)} chunks",
        chunks=chunks,
        total_chunks=len(chunks),
        total_tokens=total_tokens
    )

async def _chunk_and_update_document(
    request: ChunkApiRequest, text: str, existing_doc: Optional[Dict[str, Any]]
) -> bool:
    """
    Private function to chunk text and update Elasticsearch document
    
    Args:
        itemid: Unique identifier for the document
        index_name: Elasticsearch index name
        text: Text content to be chunked
        chunk_token_limit: Maximum tokens per chunk
        overlap_tokens: Number of overlapping tokens between chunks
        
    Returns:
        ChunkApiResponse object with status and details
    """
     # Format this response.chunks from array of string to object like [{"text":"", "embeddings":[]}]
    # Core chunking
    chunk_response = _chunk_text(
        ChunkRequest(
            text=text,
            chunk_token_limit=request.chunk_token_limit,
            overlap_tokens=request.overlap_tokens
        )
    )
    chunks = [
        {"text": chunk} for chunk in chunk_response.chunks
    ]

    # Update existing document using bulk_update
    logger.info("Updating existing document using bulk_update...")
    bulk_update_body = [
        {
            "update": {"_id": existing_doc.get("_id"), "_index": request.index_name}
        },
        {
            "doc": {
                request.output_field_name: chunks
            }
        }
    ]
    update_success = await elasticsearch_service.bulk_update(request.index_name, bulk_update_body)
    return update_success

@chunking_router.post("/chunk", response_model=ChunkApiResponse)
async def chunk_content(request: ChunkApiRequest):
    """
    Main chunk API endpoint - processes text and performs chunking
    """
    try:
        logger.info(f"Received chunking request with itemid: {request.id}, IndexName: {request.index_name}, forceUpdate: {request.force_update}")
        
        # Initialize variables
        es_indexed = False
        document_id = None
        action_performed = None
        text=""
        
        if elasticsearch_service.is_initialized:
            # Check if document exists
            existing_doc = await elasticsearch_service.get_document_by_itemid(
                request.index_name, 
                request.id
            )
            
            if existing_doc:
                logger.info(f"Document already exists for itemid: {request.id}")
                # Read body_content from existing_doc
                input_content = existing_doc.get('_source', {}).get(request.input_field_name)
                #update with actual embedding field name
                content_chunks = existing_doc.get('_source', {}).get(request.output_field_name)

                #Add a check if request.forceUpdate is false and body_chunks exist then return early
                if not request.force_update and content_chunks:
                    logger.info(f"Document already chunked for itemid: {request.id}, skipping chunking")
                    return ChunkApiResponse(
                        status="ignored",
                        message=f"Document already chunked for itemid: {request.id}",
                        elasticsearch_indexed=False,
                        document_id=existing_doc.get("_id"),
                        action_performed="noop"
                    )
                #Else if request.forceUpdate is True
                elif request.force_update:
                    logger.info(f"Force update requested for itemid: {request.id}, proceeding with chunking")
                    # If body_content is not empty, use it for chunking
                    if input_content:
                        text = input_content
                    else:
                        logger.warning(f"No {request.input_field_name} found for chunking")
                        return ChunkApiResponse(
                            status="warning",
                            message=f"No {request.input_field_name} found for itemid: {request.id}",
                            elasticsearch_indexed=False
                        )

                update_success = await _chunk_and_update_document(request=request, text=text, existing_doc=existing_doc)
                
                if update_success:
                    es_indexed = True
                    document_id = existing_doc.get("_id")
                    action_performed = "updated"
                    logger.info(f"Document updated for itemid: {request.id}")
                
            else:
                # Document doesn't exist
                logger.info("Document does not exist")
                return ChunkApiResponse(
                    status="error",
                    message=f"Document not found for itemid: {request.id}",
                    elasticsearch_indexed=False
                )
                
        else:
            logger.warning("Elasticsearch REST service not available")
            return ChunkApiResponse(
                status="error",
                message="Elasticsearch service not available",
                elasticsearch_indexed=False
            )
        
        return ChunkApiResponse(
            status="success",
            message=f"Content chunked successfully.",
            elasticsearch_indexed=es_indexed,
            document_id=document_id,
            action_performed=action_performed
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in chunk_content: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@chunking_router.get("/chunk/info")
async def chunk_info():
    """Get information about chunking service"""
    from services.chunking import is_initialized
    
    return {
        "service": "SmartChunker",
        "status": "initialized" if is_initialized else "not initialized",
        "encoding": "cl100k_base (GPT-3.5-turbo/GPT-4 compatible)",
        "features": [
            "Sentence-aware chunking",
            "Token-based splitting",
            "Configurable overlap",
            "Long sentence handling"
        ]
    }


@chunking_router.get("/chunk/{id}")
async def get_chunks(id: str, index_name: str, input_field_name: str = "body_content"):
    """Get existing chunks for an itemid"""
    if not elasticsearch_service.is_initialized:
        raise HTTPException(status_code=503, detail="Elasticsearch service not available")
    
    try:
        document = await elasticsearch_service.get_document_by_itemid(index_name, id)
        if document:
            input_content = document.get("_source", {}).get(input_field_name)
            if input_content:
                chunk_response = _chunk_text(
                    ChunkRequest(
                        text=input_content,
                        chunk_token_limit=100,  # Example token limit
                        overlap_tokens=20       # Example overlap tokens
                    )
                )
                return {
                    "status": "found",
                    "itemid": id,
                    "chunks": chunk_response.chunks,
                    "total_chunks": chunk_response.total_chunks,
                    "total_tokens": chunk_response.total_tokens
                }
            else:
                return {
                    "status": "found",
                    "itemid": id,
                    "message": f"No {input_field_name} found in the document"
                }
        else:
            return {
                "status": "not_found",
                "itemid": id,
                "message": "Document not found"
            }
    except Exception as e:
        logger.error(f"Error retrieving chunks for itemid {id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

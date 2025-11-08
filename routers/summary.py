from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import time
import json
import asyncio
import logging
import re

# Import services and models
from services.search_client import ElasticsearchClient
from summary_agent.summary_agent_crew import SummaryGeneratorPipeline
from models import SummaryOnlyRequest, NLPEnrichmentRequest, NLPEnrichmentResponse, NLPEnrichmentData
from services.nlp_enrichment import get_nlp_service
from llm_integration.client import get_azure_crew_llm

logger = logging.getLogger(__name__)

summary_router = APIRouter(tags=["summary"])

@summary_router.post("/nlp-enrichment", response_model=NLPEnrichmentResponse)
async def get_nlp_enrichment(request: NLPEnrichmentRequest):
    """
    Perform NLP enrichment on search results without generating summary
    """
    try:
        start_time = time.time()
        
        # Step 1: Search for results
        search_client = ElasticsearchClient()
        search_response = await search_client.search_for_summary(
            query=request.query,
            top_n=request.top_results,
            country=request.country,
            language=request.language
        )

        if not search_response.results:
            raise HTTPException(status_code=404, detail="No results found for your query")

        # Step 2: Perform NLP enrichment
        nlp_service = get_nlp_service()
        nlp_enrichment_data = []
        
        for i, result in enumerate(search_response.results, 1):
            enrichment = {}
            
            if nlp_service.is_initialized:
                try:
                    enrichment = nlp_service.enrich_content(
                        title=result.title or "",
                        description=result.content or "",  
                        body_content=getattr(result, "body_content", "") or ""
                    )
                except Exception as e:
                    logger.warning(f"NLP enrichment failed for result {i}: {e}")
                    enrichment = {
                        "entities": [],
                        "keyword_phrases": [],
                        "potential_questions": []
                    }
            else:
                enrichment = {
                    "entities": [],
                    "keyword_phrases": [],
                    "potential_questions": []
                }
            
            nlp_data = NLPEnrichmentData(
                source_index=i,
                title=result.title or "",
                description=result.content or "",
                entities=enrichment.get("entities", []),
                keyword_phrases=enrichment.get("keyword_phrases", []),
                potential_questions=enrichment.get("potential_questions", [])
            )
            nlp_enrichment_data.append(nlp_data)

        processing_time = time.time() - start_time
        
        return NLPEnrichmentResponse(
            query=request.query,
            nlp_enrichment_data=nlp_enrichment_data,
            source_count=len(search_response.results),
            total_results_available=search_response.total_count,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in NLP enrichment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to perform NLP enrichment: {str(e)}")

@summary_router.post("/summary")
async def generate_summary_only(request: SummaryOnlyRequest):
    """
    Generate AI-powered summary from search results without NLP enrichment - Streaming Response
    """
    async def generate_summary_stream():
        try:
            # Initial status
            yield f"data: {json.dumps({'status': 'starting', 'message': 'Initializing search...'})}\n\n"
            
            start_time = time.time()
            
            # Step 1: Search for results
            yield f"data: {json.dumps({'status': 'searching', 'message': 'Searching for relevant content...'})}\n\n"
            
            search_client = ElasticsearchClient()
            search_response = await search_client.search_for_summary(
                query=request.query,
                top_n=request.top_results,
                country=request.country,
                language=request.language
            )

            if not search_response.results:
                yield f"data: {json.dumps({'status': 'error', 'message': 'No results found for your query', 'is_final': True})}\n\n"
                return

            yield f"data: {json.dumps({'status': 'found_results', 'message': f'Found {len(search_response.results)} results, preparing for summary generation...'})}\n\n"

            # Step 2: Extract data for LLM (title, description, body content)
            search_results = []
            for i, result in enumerate(search_response.results, 1):
                search_result = {
                    "source_index": i,
                    "title": result.title or "",
                    "url": result.url or "",
                    "score": result.score,
                    "description": result.content or "",
                    "body_content": getattr(result, "body_content", "") or ""
                }
                search_results.append(search_result)

            yield f"data: {json.dumps({'status': 'generating', 'message': 'Generating AI summary...'})}\n\n"

            inputs = {
                "user_query": request.query,
                "search_results": search_results
            }
            
            llm = get_azure_crew_llm()
            pipeline = SummaryGeneratorPipeline(llm).crew()
            summary_result = pipeline.kickoff(inputs=inputs)
            summary_text = summary_result.output if hasattr(summary_result, "output") else str(summary_result)
            
            # Step 4: Stream the summary in chunks
            yield f"data: {json.dumps({'status': 'streaming_summary', 'message': 'Streaming summary...'})}\n\n"
            
            # Split summary into sentences and stream them
            sentences = re.split(r'(?<=[.!?])\s+', summary_text)
            
            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    chunk_data = {
                        'status': 'summary_chunk',
                        'chunk': sentence.strip(),
                        'chunk_index': i,
                        'total_chunks': len(sentences),
                        'is_final': False
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                    await asyncio.sleep(0.1)  
            
            processing_time = time.time() - start_time
            final_data = {
                'status': 'completed',
                'query': request.query,
                'summary': summary_text,
                'source_count': len(search_response.results),
                'total_results_available': search_response.total_count,
                'processing_time': processing_time,
                'is_final': True
            }
            yield f"data: {json.dumps(final_data)}\n\n"
            
        except Exception as e:
            logger.error(f"Error in streaming summary: {str(e)}")
            error_data = {
                'status': 'error',
                'message': f'Failed to generate summary: {str(e)}',
                'is_final': True
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_summary_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@summary_router.get("/summary/info")
async def summary_info():
    """Get information about summary service"""
    
    return {
        "service": "Summary Generator",
        "status": "available",
        "features": [
            "AI-powered summary generation",
            "Streaming response support",
            "Multi-language search support",
            "Elasticsearch integration",
            "Lutron product knowledge integration"
        ],
        "endpoints": [
            "/api/summary - Generate streaming summary",
            "/api/nlp-enrichment - Get NLP enriched data"
        ]
    }

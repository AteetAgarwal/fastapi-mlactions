from typing import List, Optional, Dict
from pydantic import BaseModel

class SummaryOnlyRequest(BaseModel):
    query: str
    top_results: int = 5
    country: str = "us"
    language: str = "en"

# Models for NLP Enrichment endpoint
class NLPEnrichmentRequest(BaseModel):
    query: str
    top_results: int = 5
    country: str = "us"
    language: str = "en"

class NLPEnrichmentData(BaseModel):
    source_index: int
    title: str
    description: str
    entities: list[str]
    keyword_phrases: list[str]
    potential_questions: list[str]

class NLPEnrichmentResponse(BaseModel):
    query: str
    nlp_enrichment_data: list[NLPEnrichmentData]
    source_count: int
    total_results_available: int
    processing_time: Optional[float] = None
    
class SearchResult(BaseModel):
    title: str
    content: str
    url: Optional[str] = ""
    score: Optional[float] = 0.0
    # Enhanced fields for better summaries
    body_content: Optional[str] = ""
    additional_titles: Optional[List[str]] = []
    main_title: Optional[List[str]] = []
    highlight: Optional[Dict[str, List[str]]] = {}
    keywords: Optional[Dict[str, List[str]]] = {}
    

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_count: int
    query: str

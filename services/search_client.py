import httpx
import asyncio
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import logging

from models import (SearchResult, SearchResponse)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ElasticsearchClient:
    def __init__(self):
        self.base_url = "https://elastic-ae1dev-app01-staging.azurewebsites.net"
        self.client_id = "5DF3759E-D450-4487-90FF-C5C0F1F1639C"
        self.client_secret = "RDE3QzVBRUEtQ0ExOS00ODM5LTgxQzgtRjYyQ0MxODNDMTAx"
    
    async def search(self, query: str, top_n: int = 5, country: str = "us", language: str = "en") -> SearchResponse:
        """Search using the existing Elasticsearch API and return top N results"""
        
        headers = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'Content-Type': 'application/json'
        }
        
        payload = {
            "search_keyword": query,
            "search_scope": "all",
            "page_number": 1,
            "page_size": top_n,
            "country": country,
            "language": language
        }
        
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/e-search/api/search?is_all_fields=true&include_body_with_all_fields=true",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )

                print(f"Search API response status: {response}")
                response.raise_for_status()
                data = response.json()
                hits = data.get("data", {}).get("hits", [])
                
                results = []
                
                for hit in hits[:top_n]:
                    source = hit.get("source", {})
                    
                    description = source.get("description", "")
                    if isinstance(description, list):
                        description = " ".join(str(item) for item in description)
                    elif not isinstance(description, str):
                        description = str(description)

                    # Extract enhanced content
                    body_content = source.get("body_content", "") or source.get("body_content_semantic", "")
                    additional_titles = source.get("additional_titles", []) or source.get("additional_titles_semantic", [])
                    main_title = source.get("main_title", [])
                    

                    additional_titles = [title for title in additional_titles if title.strip()]
                    
                    # Extract keyword categories for context
                    keywords = {
                        "brand": source.get("keyword_brand", []),
                        "function": source.get("keyword_function", []),
                        "category": source.get("keyword_category", []),
                        "aesthetic": source.get("keyword_aesthetic", []),
                        "content_type": source.get("keyword_content_type", [])
                    }
                    

                    results.append(SearchResult(
                        title=source.get("title", "No title"),
                        content=description,
                        url=source.get("url", ""),
                        score=hit.get("score", 0.0),
                        body_content=body_content,
                        additional_titles=additional_titles,
                        main_title=main_title,
                        highlight=hit.get("highlight", {}),
                        keywords=keywords
                    ))

                return SearchResponse(
                    results=results,
                    total_count=data.get("data", {}).get("total", len(results)),
                    query=query
                )
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error from search API: {e.response.status_code} - {e.response.text}")
                raise Exception(f"Search API returned error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Search API error: {str(e)}")
                raise Exception(f"Failed to search: {str(e)}")

        
    def get_enhanced_content_for_summary(self, result: SearchResult) -> str:
        """
        Extract and format the most relevant content for LLM summarization
        This creates a rich context that mimics what Google uses for feature snippets
        """
        content_parts = []
        
        if result.main_title:
            content_parts.append(f"Main Topic: {' | '.join(result.main_title)}")
        
        if result.content:
            content_parts.append(f"Description: {result.content}")
        
        if result.highlight:
            highlights = []
            for field, excerpts in result.highlight.items():
                if field in ['body_content', 'description', 'title']:
                    clean_excerpts = [excerpt.replace('<em>', '').replace('</em>', '') for excerpt in excerpts]
                    highlights.extend(clean_excerpts)
            
            if highlights:
                content_parts.append(f"Key Information: {' '.join(highlights[:3])}") 
        

        if result.additional_titles:
   
            relevant_titles = [title for title in result.additional_titles[:5] if len(title) > 5]
            if relevant_titles:
                content_parts.append(f"Related Topics: {' | '.join(relevant_titles)}")
        

        if result.keywords:
            context_parts = []
            for key, values in result.keywords.items():
                if values and key in ['brand', 'function', 'category']:
                    context_parts.append(f"{key.title()}: {', '.join(values[:3])}")
            
            if context_parts:
                content_parts.append(f"Context: {' | '.join(context_parts)}")
        
      
        if result.body_content and len(result.body_content) > 100:

            snippet = result.body_content[:500] + "..." if len(result.body_content) > 500 else result.body_content
            content_parts.append(f"Additional Details: {snippet}")
        
        return "\n\n".join(content_parts)
            
    async def search_for_summary(self, query: str, top_n: int = 5, country: str = "us", language: str = "en") -> List[str]:
        """
        Convenience method that returns formatted content ready for LLM summarization
        """
        search_response = await self.search(query, top_n=top_n, country=country, language=language)

        for result in search_response.results:
            enhanced_content = self.get_enhanced_content_for_summary(result)
            result.content = enhanced_content

        return search_response
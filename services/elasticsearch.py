import logging
import httpx
from typing import Optional, Dict, Any, List
from services.azure_keyvault import azure_kv_service
import json

logger = logging.getLogger(__name__)

class ElasticsearchService:
    """Service to interact with Elasticsearch using REST API"""
    
    def __init__(self):
        self.base_url = None
        self.api_key = None
        self.headers = {}
        self.is_initialized = False
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Elasticsearch REST client with Azure Key Vault credentials"""
        try:
            # Check if Azure Key Vault service is available
            if not azure_kv_service.is_initialized:
                logger.warning("Azure Key Vault service not initialized, Elasticsearch service will not be available")
                return
                
            # Get Elasticsearch configuration from Key Vault
            es_config = azure_kv_service.get_elasticsearch_config()
            
            if not es_config["url"]:
                logger.error("Elasticsearch URL not available")
                return
            
            if not es_config["api_key"]:
                logger.error("Elasticsearch API Key not available")
                return
            
            self.base_url = es_config["url"].rstrip('/')
            self.api_key = es_config["api_key"]
            
            # Set up headers for API key authentication
            self.headers = {
                "Authorization": f"ApiKey {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Test connection
            if self._test_connection():
                self.is_initialized = True
                logger.info("Elasticsearch REST client initialized and connected successfully")
            else:
                logger.error("Failed to connect to Elasticsearch")
                
        except Exception as e:
            logger.error(f"Unexpected error initializing Elasticsearch REST client: {e}")
    
    def _test_connection(self) -> bool:
        """Test connection to Elasticsearch cluster"""
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{self.base_url}/_cat",
                    headers=self.headers,
                    timeout=30.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def search(self, index: str, query: Dict[str, Any], size: int = 10) -> Optional[Dict[str, Any]]:
        """
        Search documents in Elasticsearch using REST API
        
        Args:
            index: Index name to search
            query: Elasticsearch query
            size: Number of results to return
            
        Returns:
            Search results or None if error
        """
        if not self.is_initialized:
            logger.error("Elasticsearch REST client not initialized")
            return None
        
        try:
            search_body = {
                "query": query,
                "size": size
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/{index}/_search",
                    headers=self.headers,
                    json=search_body,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Search completed on index: {index}")
                    return response.json()
                else:
                    logger.error(f"Search failed with status {response.status_code}: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error searching Elasticsearch: {e}")
            return None
    
    async def get_document_by_itemid(self, index: str, itemid: str) -> Optional[Dict[str, Any]]:
        """
        Get document by itemid using search query
        
        Args:
            index: Index name
            id: Item ID to search for
            
        Returns:
            Document or None if not found
        """
        query = {
            "term": {
                "_id": itemid
            }
        }
        
        result = await self.search(index, query, size=1)
        if result and result.get("hits", {}).get("hits"):
            return result["hits"]["hits"][0]
        return None
    
    async def bulk_update(self, index: str, updates: List[Dict[str, Any]]) -> bool:
        """
        Bulk update documents in Elasticsearch using _bulk endpoint
        
        Args:
            index: Index name
            updates: List of update actions
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized:
            logger.error("Elasticsearch REST client not initialized")
            return False
        
        try:
           # Convert list of dictionaries to newline-delimited JSON
            bulk_lines = []
            for operation in updates:
                bulk_lines.append(json.dumps(operation))
            
            bulk_body = "\n".join(bulk_lines) + "\n"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/{index}/_bulk",
                    headers=self.headers,
                    data=bulk_body,
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    updated_count = sum(1 for item in result.get("items", []) if "update" in item and "status" in item["update"] and item["update"]["status"] == 200)
                    logger.info(f"Bulk update completed. Updated {updated_count} documents.")
                    return True
                else:
                    logger.error(f"Bulk update failed with status {response.status_code}: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error during bulk update: {e}")
            return False

    async def get_cluster_health(self) -> Optional[Dict[str, Any]]:
        """Get Elasticsearch cluster health using REST API"""
        if not self.is_initialized:
            logger.error("Elasticsearch REST client not initialized")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/_cluster/health",
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Cluster health check failed with status {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting cluster health: {e}")
            return None

class LazyElasticsearchService:
    """Lazy-loading proxy for Elasticsearch Service"""
    def __init__(self):
        self._service = None
    
    def _get_service(self):
        if self._service is None:
            self._service = ElasticsearchService()
        return self._service
    
    @property
    def is_initialized(self):
        if self._service is None:
            return False
        return self._service.is_initialized
    
    async def search(self, index: str, query: dict, size: int = 10):
        return await self._get_service().search(index, query, size)
    
    async def index_document(self, index: str, document: dict, doc_id: str = None):
        return await self._get_service().index_document(index, document, doc_id)
    
    async def delete_document(self, index: str, doc_id: str):
        return await self._get_service().delete_document(index, doc_id)
    
    async def create_index(self, index: str, mapping: dict = None):
        return await self._get_service().create_index(index, mapping)
    
    async def delete_index(self, index: str):
        return await self._get_service().delete_index(index)
    
    def get_cluster_health(self):
        return self._get_service().get_cluster_health()

# Global instance
elasticsearch_service = LazyElasticsearchService()
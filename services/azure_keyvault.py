import os
import logging
from typing import Optional
from azure.keyvault.secrets import SecretClient
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.core.exceptions import AzureError


logger = logging.getLogger(__name__)

class AzureKeyVaultService:
    """Service to interact with Azure Key Vault"""
    
    def __init__(self):
        self.client = None
        self.is_initialized = False
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Azure Key Vault client"""
        try:
            key_vault_url = f"https://{os.getenv('AZ_KEYVAULT_NAME')}.vault.azure.net/"
            if not key_vault_url:
                logger.warning("AZ_KEYVAULT_NAME not found in environment variables")
                return
            
            # Try to use service principal credentials first
            client_id = os.getenv("AZ_KEYVAULT_CLIENT_ID")
            client_secret = os.getenv("AZ_KEYVAULT_CLIENT_SECRET")
            tenant_id = os.getenv("AZ_KEYVAULT_TENANT_ID")
            
            if client_id and client_secret and tenant_id:
                logger.info("Using service principal credentials for Key Vault access")
                credential = ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret
                )
            else:
                logger.info("Using default Azure credentials for Key Vault access")
                credential = DefaultAzureCredential()
            
            self.client = SecretClient(vault_url=key_vault_url, credential=credential)
            
            # Test the connection with a simple call
            try:
                # Try to list properties to test the connection
                # This will fail if credentials or network are bad
                test_result = list(self.client.list_properties_of_secrets(max_page_size=1))
                logger.info("Azure Key Vault connection test successful")
                self.is_initialized = True
            except Exception as test_error:
                logger.warning(f"Azure Key Vault connection test failed: {test_error}")
                self.is_initialized = False
                self.client = None
                return
            
            logger.info("Azure Key Vault client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure Key Vault client: {e}")
            self.is_initialized = False
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Retrieve a secret from Azure Key Vault
        
        Args:
            secret_name: Name of the secret to retrieve
            
        Returns:
            Secret value or None if not found
        """
        if not self.is_initialized:
            logger.error("Azure Key Vault client not initialized")
            return None
        
        try:
            logger.info(f"Retrieving secret: {secret_name}")
            secret = self.client.get_secret(secret_name)
            logger.info(f"Successfully retrieved secret: {secret_name}")
            return secret.value
        except AzureError as e:
            logger.warning(f"Azure error retrieving secret {secret_name}: {e}")
            # Mark service as not initialized if we can't connect
            self.is_initialized = False
            return None
        except Exception as e:
            logger.warning(f"Network/connection error retrieving secret {secret_name}: {e}")
            # Mark service as not initialized if we can't connect  
            self.is_initialized = False
            return None
    
    def get_elasticsearch_config(self) -> dict:
        """
        Get Elasticsearch configuration from Key Vault
        
        Returns:
            Dictionary containing Elasticsearch URL and API key
        """
        config = {
            "url": None,
            "api_key": None
        }
        
        try:
            # Get Elasticsearch URL
            es_url = self.get_secret("ConnectionStrings--Elasticsearch--Url")
            if es_url:
                config["url"] = es_url
                logger.info("Elasticsearch URL retrieved from Key Vault")
            else:
                logger.warning("Elasticsearch URL not found in Key Vault")
            
            # Get Elasticsearch API Key
            es_api_key = self.get_secret("ConnectionStrings--Elasticsearch--WriteApiKey")
            if es_api_key:
                config["api_key"] = es_api_key
                logger.info("Elasticsearch API Key retrieved from Key Vault")
            else:
                logger.warning("Elasticsearch API Key not found in Key Vault")
            
            return config
            
        except Exception as e:
            logger.error(f"Error retrieving Elasticsearch configuration: {e}")
            return config

class LazyAzureKeyVaultService:
    """Lazy-loading proxy for Azure Key Vault Service"""
    def __init__(self):
        self._service = None
    
    def _get_service(self):
        if self._service is None:
            self._service = AzureKeyVaultService()
        return self._service
    
    @property
    def is_initialized(self):
        if self._service is None:
            return False
        return self._service.is_initialized
    
    def get_secret(self, secret_name: str):
        return self._get_service().get_secret(secret_name)
    
    def get_elasticsearch_config(self):
        return self._get_service().get_elasticsearch_config()

# Global instance
azure_kv_service = LazyAzureKeyVaultService()
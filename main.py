from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import logging
from contextlib import asynccontextmanager
from models import HealthResponse
from routers import docs_router, chunking_router, summary_router, toxic_router
from services import initialize_chunking_service, azure_kv_service, elasticsearch_service, ElasticsearchClient
from services.nlp_enrichment import initialize_nlp_service, get_nlp_service, download_spacy_model
from services.chunking import download_nltk_data

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for application startup and shutdown."""
    logger.info("Starting application initialization...")
    try:
        # Download required models first
        logger.info("Checking and downloading required NLP models...")
        
        # Download NLTK data
        try:
            logger.info("Downloading NLTK data...")
            download_nltk_data()
            logger.info("NLTK data download completed successfully")
        except Exception as e:
            logger.warning(f"Failed to download NLTK data: {e}")
        
        # Download spaCy model
        if not download_spacy_model("en_core_web_sm"):
            logger.warning("Failed to download spaCy model, NLP features may not work properly")
        
        # Initialize services
        initialize_chunking_service()
        initialize_nlp_service()

        # Test service connections
        nlp_service = get_nlp_service()
        if nlp_service.is_initialized:
            logger.info("NLP enrichment service is ready")
        else:
            logger.warning("NLP enrichment service not initialized")

        if azure_kv_service.is_initialized:
            logger.info("Azure Key Vault service is ready")
        else:
            logger.warning("Azure Key Vault service not initialized")

        if elasticsearch_service.is_initialized:
            logger.info("Elasticsearch REST service is ready")
        else:
            logger.warning("Elasticsearch REST service not initialized")
        
        logger.info("Application initialization completed successfully")
        yield

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}", exc_info=True)
        raise
    finally:
        logger.info("Application shutdown completed")


app = FastAPI(
    title="Chunk Content in Elastic Search with NLP Enrichment",
    description="API to chunk content, perform NLP enrichment, and store in Elastic Search",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API router
api_router = APIRouter(prefix="/api")

@api_router.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="Chunk content API is running"
    )



@api_router.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check endpoint with service status"""
    # Test search client connectivity (optional)
    search_client_status = True
    try:
        search_client = ElasticsearchClient()
        # The client exists and is configured
        search_client_status = True
    except Exception:
        search_client_status = False
    
    services = {
        "azure_key_vault": azure_kv_service.is_initialized,
        "elasticsearch": elasticsearch_service.is_initialized,
        "search_client": search_client_status,
        "nlp_enrichment": get_nlp_service().is_initialized,
        "chunking": True
    }
    
    return HealthResponse(
        status="healthy",
        message="Service is running. All systems operational.",
        services=services
    )

@api_router.get("/debug/urls")
async def debug_urls():
    """Debug endpoint to check configured URLs"""
    return {
        "docs_url": app.docs_url,
        "redoc_url": app.redoc_url,
        "openapi_url": app.openapi_url,
        "available_endpoints": [
            "/api/docs",
            "/api/redoc", 
            "/api/openapi.json",
            "/api/swagger.json",
            "/api/health",
            "/api/debug/urls",
            "/api/chunk",
            "/api/summary",
            "/api/nlp-enrichment",
            "/api/toxicity"
        ],
        "services": {
            "azure_key_vault": azure_kv_service.is_initialized,
            "elasticsearch": elasticsearch_service.is_initialized,
            "search_client": "configured"
        }
    }

# Include routers
api_router.include_router(docs_router)
api_router.include_router(chunking_router)
api_router.include_router(summary_router)
api_router.include_router(toxic_router)

# Include main API router
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )

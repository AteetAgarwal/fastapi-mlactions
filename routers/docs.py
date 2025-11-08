from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

docs_router = APIRouter()

@docs_router.get("/openapi.json", include_in_schema=False)
async def openapi_json():
    """OpenAPI JSON schema"""
    from main import app
    return JSONResponse(app.openapi())

@docs_router.get("/swagger.json", include_in_schema=False)
async def swagger_json():
    """Swagger JSON schema (compatibility endpoint)"""
    from main import app
    return JSONResponse(app.openapi())

@docs_router.get("/docs", include_in_schema=False)
async def aks_docs():
    """Custom Swagger UI documentation"""
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json", 
        title="Chunk Content API Documentation"
    )

@docs_router.get("/redoc", include_in_schema=False)
async def aks_redoc():
    """Custom ReDoc documentation"""
    return get_redoc_html(
        openapi_url="/api/openapi.json", 
        title="Chunk Content API Documentation"
    )
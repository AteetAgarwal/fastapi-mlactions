# Chunk Content in Elasticsearch - FastAPI Application

## Overview
This project provides a production-ready FastAPI application for chunking text content and storing it in Elasticsearch with Azure Key Vault integration for secure credential management.

## Project Structure
```
PythonFastAPI/
├── main.py                     # Main FastAPI application entry point
├── requirements.txt            # Python dependencies
├── .env                       # Environment variables (Azure credentials)
├── Dockerfile                 # Docker containerization
├── SETUP.md                   # This setup guide
├── README.md                  # Project overview
│
├── .vscode/                   # VS Code configuration
│   └── launch.json           # Debug configurations
│
├── configurations/           # Kubernetes deployment files
│   ├── k8s-deployment.yaml  # AKS deployment manifest
│   └── service.yaml         # Kubernetes service
│
├── models/                   # Pydantic data models
│   ├── __init__.py
│   ├── chunk_model.py       # Chunking request/response models
│   ├── health_model.py      # Health check models
│   └── key_vault_model.py   # Key Vault models
│
├── routers/                  # FastAPI route handlers
│   ├── __init__.py
│   ├── docs.py              # Documentation routes
│   └── chunking.py          # Text chunking API endpoints
│
└── services/                # Business logic services
    ├── __init__.py
    ├── chunking.py          # Smart text chunking with NLTK
    ├── azure_keyvault.py    # Azure Key Vault integration
    ├── elasticsearch.py     # Elasticsearch REST API client
    └── html_stripper.py     # HTML content cleaning
```

## Features

### 🔧 **Text Chunking**
- **Smart sentence-aware chunking** using NLTK's punkt tokenizer
- **Token-based splitting** with tiktoken (GPT-3.5-turbo/GPT-4 compatible)
- **HTML content cleaning** with advanced text preprocessing
- **Configurable chunk size and overlap** for optimal context preservation
- **Fallback mechanisms** for handling edge cases and long sentences
- **Word tokenization** for sentences exceeding token limits

## Installation & Setup

### 1. **Prerequisites**
```bash
# Python 3.11 or higher
# Azure subscription with Key Vault access
# Elasticsearch cluster
```

### 2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 3. **Environment Configuration**
Create a `.env` file in the project root:
```env
# Azure Key Vault Configuration
AZ_KEYVAULT_NAME=WebAPI-aw1dev-kv01
AZ_KEYVAULT_CLIENT_ID=your-client-id
AZ_KEYVAULT_CLIENT_SECRET=your-client-secret
AZ_KEYVAULT_TENANT_ID=your-tenant-id

# Application Configuration
PORT=8000
LOG_LEVEL=INFO
```

### 4. **Azure Key Vault Setup**
Store your Elasticsearch credentials in Azure Key Vault:
```bash
# Elasticsearch URL
az keyvault secret set --vault-name "WebAPI-aw1dev-kv01" \
  --name "ConnectionStrings--Elasticsearch--Url" \
  --value "https://your-elasticsearch-cluster.com"

# Elasticsearch API Key
az keyvault secret set --vault-name "WebAPI-aw1dev-kv01" \
  --name "ConnectionStrings--Elasticsearch--WriteApiKey" \
  --value "your-elasticsearch-api-key"
```

### 5. **Run the Application**

#### **Local Development**
```bash
python main.py
```

#### **With Uvicorn**
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The application will be available at:
- **API**: http://localhost:8000/api/
- **Documentation**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## API Endpoints

### **Core Endpoints**

#### **1. Health Check**
```http
GET /api/health
```
Returns service status and health information including Azure Key Vault and Elasticsearch connectivity.

#### **2. Chunk Content**
```http
POST /api/chunk
Content-Type: application/json

{
    "id": "document-123",
    "index_name": "documents",
    "input_field_name": "body_content",
    "output_field_name": "body_content_embeddings",
    "force_update": false,
    "chunk_token_limit": 200,
    "overlap_tokens": 50
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Content chunked successfully.",
    "elasticsearch_indexed": true,
    "document_id": "document-123",
    "action_performed": "updated"
}
```

#### **3. Get Chunks**
```http
GET /api/chunk/document-123?index_name=documents&input_field_name=body_content
```

#### **4. Chunking Service Info**
```http
GET /api/chunk/info
```

### **Debug Endpoints**

#### **5. Debug URLs**
```http
GET /api/debug/urls
```
Returns available endpoints and service status.

### **Documentation Endpoints**
- `GET /api/docs` - Swagger UI
- `GET /api/redoc` - ReDoc documentation
- `GET /api/openapi.json` - OpenAPI schema
- `GET /api/swagger.json` - Swagger JSON schema

## Architecture

### **Service Layer**
- **[`services/chunking.py`](services/chunking.py)**: Smart text chunking with NLTK and tiktoken
- **[`services/azure_keyvault.py`](services/azure_keyvault.py)**: Secure credential management
- **[`services/elasticsearch.py`](services/elasticsearch.py)**: Elasticsearch operations via REST API
- **[`services/html_stripper.py`](services/html_stripper.py)**: HTML content cleaning and preprocessing

### **Router Layer**
- **[`routers/chunking.py`](routers/chunking.py)**: API endpoints for text chunking operations
- **[`routers/docs.py`](routers/docs.py)**: Documentation and utility routes

### **Models Layer**
- **[`models/chunk_model.py`](models/chunk_model.py)**: Chunking request/response models
- **[`models/health_model.py`](models/health_model.py)**: Health check models
- **[`models/key_vault_model.py`](models/key_vault_model.py)**: Key Vault models

## Chunking Algorithm

### **1. Text Preprocessing**
- Uses [`clean_text_advanced`](services/html_stripper.py) to clean HTML content
- Unescapes HTML entities and removes tags
- Normalizes Unicode characters

### **2. Sentence Tokenization**
- Uses NLTK's `punkt_tab` tokenizer for natural sentence boundaries
- Downloads required NLTK data automatically during initialization

### **3. Token Limit Check**
- Checks if sentences exceed `chunk_limit + 10%` buffer
- Uses tiktoken with `cl100k_base` encoding (GPT-3.5-turbo/GPT-4)

### **4. Word Tokenization**
- For oversized sentences, applies NLTK word tokenization
- Creates subchunks respecting token limits
- Fallback to simple split if word tokenization fails

### **5. Smart Accumulation**
- Accumulates sentences/subchunks until token limit is reached
- Maintains configurable overlap between chunks using token-based overlap
- Handles large subchunks as separate entities

## Configuration

### **Chunking Parameters**
- **`chunk_token_limit`**: Maximum tokens per chunk (default: 100)
- **`overlap_tokens`**: Overlap between chunks (default: 20)
- **Buffer**: 10% buffer for sentence boundary detection

### **Service Parameters**
- **`PORT`**: Application port (default: 8000)
- **`LOG_LEVEL`**: Logging level (default: INFO)

### **Field Mapping**
- **`input_field_name`**: Source field for text content (default: "body_content")
- **`output_field_name`**: Target field for chunks (default: "body_content_embeddings")

## Kubernetes Deployment

### **Prerequisites**
- Azure Container Registry (ACR)
- Azure Kubernetes Service (AKS)
- Azure Key Vault with proper access policies

## Error Handling

### **Status Codes**
- **200**: Success
- **400**: Bad Request (validation errors)
- **404**: Not Found
- **500**: Internal Server Error
- **503**: Service Unavailable (Elasticsearch down)

### **Chunking Behavior**
- **Force Update**: When `force_update: true`, always rechunks content
- **Skip Existing**: When `force_update: false` and chunks exist, skips processing
- **Document Not Found**: Returns error if document doesn't exist in Elasticsearch

## Monitoring & Health Checks

### **Health Endpoints**
- **Basic**: `GET /api/` - Simple health check
- **Detailed**: `GET /api/health` - Service status with dependencies

### **Service Status Checks**
```json
{
    "status": "healthy",
    "message": "Service is running. All systems operational.",
    "services": {
        "azure_key_vault": true,
        "elasticsearch": true,
        "chunking": true
    }
}
```

## Security

### **Best Practices**
- Credentials stored in Azure Key Vault
- Service principal authentication for Key Vault access
- API key-based Elasticsearch access
- Non-root container user
- Resource limits in Kubernetes
- Environment variable configuration
- No sensitive data in logs

### **Container Security**
- Uses Python 3.11-slim base image
- Non-root user (`appuser`)
- Health checks for monitoring
- Minimal attack surface

## Troubleshooting

### **Common Issues**

#### **1. NLTK Data Missing**
```bash
# Service automatically downloads, but manual download:
python -c "import nltk; nltk.download('punkt_tab'); nltk.download('stopwords')"
```

#### **2. Azure Key Vault Access**
```bash
# Verify service principal permissions
az keyvault secret show --vault-name "WebAPI-aw1dev-kv01" --name "test-secret"
```

#### **3. Elasticsearch Connection**
```bash
# Test connectivity
curl -H "Authorization: ApiKey your-api-key" https://your-elasticsearch-cluster.com/_cat
```

#### **4. Chunking Service Not Initialized**
- Check logs for initialization errors
- Verify NLTK data download
- Ensure tiktoken encoding initialization

#### **5. Document Not Found**
- Verify document exists in Elasticsearch index
- Check index name and document ID
- Ensure proper field mapping
# BridgeMart FastAPI Backend

FastAPI backend service for BridgeMart AI workloads and API orchestration.

## Project Structure

```
server/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Environment-based configuration
│   ├── routers/             # API route handlers
│   │   ├── health_router.py # Health check endpoints
│   │   ├── llm_router.py    # LLM-related endpoints
│   │   └── ai_router.py     # AI/ML endpoints
│   ├── services/            # Business logic layer
│   │   ├── llm_service.py   # LLM operations (Ollama)
│   │   └── ai_service.py    # AI/ML operations (PyTorch)
│   └── schemas/             # Pydantic models
│       ├── health.py        # Health check schemas
│       ├── llm.py           # LLM request/response schemas
│       └── ai.py            # AI request/response schemas
├── requirements.txt
└── .env                     # Environment variables (create from .env.example)
```

## Setup

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai/) installed and running (for LLM features)

### Installation

1. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

4. Configure environment variables in `.env` as needed.

### Running the Server

Start the development server with auto-reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use FastAPI CLI:

```bash
fastapi dev main.py
```

The API will be available at:

- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Health (`/health`)

- `GET /health` - Service health check
- `GET /health/ready` - Readiness check with dependency status

### Datasets (`/api/v1/datasets`)

- `POST /api/v1/datasets/embed` - Upload a CSV, index rows in PGVector, encrypt the raw dataset, upload it to IPFS, and return the completed dataset metadata synchronously
- `POST /api/v1/datasets/{listing_id}/key` - Release encryption key material after on-chain access verification
- `GET /api/v1/datasets/{listing_id}/preview` - Best-effort preview endpoint

#### Dataset Embedding Pipeline

The `/api/v1/datasets/embed` endpoint implements a complete dataset ingestion pipeline:

**Features:**

- Accepts multipart CSV upload
- Automatically detects headers in CSV files
- Loads row documents through `CSVLoader` from `langchain_community`
- Generates and stores row embeddings using LangChain PGVector
- Encrypts the raw CSV with AES-GCM and uploads ciphertext to IPFS
- Returns listing ID, dataset URL/hash, preview, vector spec, and dataset statistics

**Example Request:**

```bash
curl -X POST "http://localhost:8080/api/v1/datasets/embed" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample_dataset.csv" \
  -F "title=Sample Dataset" \
  -F "description=Example rows" \
  -F "seller=0x0000000000000000000000000000000000000001" \
  -F "price_atomic=1000000"
```

**Response Format:**

```json
{
  "listing_id": "123e4567-e89b-12d3-a456-426614174000",
  "dataset_url": "ipfs://Qm...",
  "dataset_hash": "0x...",
  "preview": { "column_names": ["age"], "rows": [["63"]] },
  "stats": {
    "total_rows": 100,
    "total_columns": 5,
    "empty_rows_skipped": 2,
    "has_header": true
  "vector_spec": {
    "model": "nomic-embed-text",
    "dimension": 768
  }
}
```

### AI (`/api/v1/ai`)

- `POST /api/v1/ai/similarity-search` - Perform semantic similarity search
- `POST /api/v1/ai/embed/query` - Embed a natural-language query

**Example Request:**

```bash
curl -X POST "http://localhost:8080/api/v1/ai/embed/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "patients with chest pain"}'
```

**Response:**

```json
{
  "original_query": "patients with chest pain",
  "query_embedding": [0.1, 0.2, ...],
  "vector_spec": {
    "model": "nomic-embed-text",
    "dimension": 768
  }
}
```

## Configuration

Configuration is managed through environment variables using Pydantic Settings. See `.env.example` for available options.

Key settings:

- `OLLAMA_HOST` - Ollama server URL (default: http://localhost:11434)
- `EMBEDDING_MODEL` - Model for embeddings (default: nomic-embed-text)
- `THINKING_MODEL` - Model for query rewriting (default: llama3.2:latest)
- `CORS_ORIGINS` - Allowed CORS origins (default: http://localhost:5173)

## Development

### Testing Endpoints

Use the interactive API docs at http://localhost:8000/docs to test endpoints.

Example curl request:

```bash
curl http://localhost:8000/health
```

### Adding New Endpoints

1. Define Pydantic schemas in the relevant feature package, such as `app/datasets/schemas.py`
2. Implement business logic in the feature service, such as `app/datasets/service.py`
3. Create route handlers in the feature router, such as `app/datasets/router.py`
4. Mount router in `app/main.py`

## Notes

The dataset embedding pipeline is fully implemented and production-ready. Other endpoints remain as skeleton implementations for future PRs.

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

### LLM (`/llm`)

- `POST /llm/embed/batch` - **Dataset embedding pipeline** - Upload CSV or .data file for batch embedding generation
- `POST /llm/embed/query` - **Query embedding pipeline** - Rewrite and embed query in one step
- `POST /llm/rewrite` - **Query rewriting** - Rewrite natural language query for better retrieval

#### Dataset Embedding Pipeline

The `/llm/embed/batch` endpoint implements a complete dataset ingestion and encoding pipeline:

**Features:**

- Accepts multipart file upload (.csv or .data format)
- Automatically detects headers in CSV files
- Transforms each record into deterministic structured text using a stable template
- Generates embeddings using Ollama embedding model
- Returns signature (embedding vectors), vectorSpec metadata, and dataset statistics

**Example Request:**

```bash
curl -X POST "http://localhost:8000/llm/embed/batch" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample_dataset.csv"
```

**Response Format:**

```json
{
  "signature": [[0.1, 0.2, ...], [0.3, 0.4, ...], ...],
  "vectorSpec": {
    "model": "nomic-embed-text",
    "dimension": 768
  },
  "stats": {
    "total_rows": 100,
    "total_columns": 5,
    "empty_rows_skipped": 2,
    "has_header": true
  },
  "filename": "sample_dataset.csv"
}
```

**Record-to-Text Template:**
Each dataset record is transformed using a deterministic template:

```
column_name: value | column_name: value | ...
```

This ensures stable, consistent text representation for embedding generation.

#### Query Rewriting and Embedding Pipeline

**Query Rewriting (`POST /llm/rewrite`)**

Rewrites natural language queries to make them more explicit and retrieval-friendly using a thinking model.

**Example Request:**

```bash
curl -X POST "http://localhost:8000/llm/rewrite" \
  -H "Content-Type: application/json" \
  -d '{"query": "heart disease data", "context": "medical dataset"}'
```

**Response:**

```json
{
  "original_query": "heart disease data",
  "rewritten_query": "medical dataset containing cardiovascular disease patient records with diagnostic features",
  "model": "llama3.2:latest"
}
```

**Query Embedding (`POST /llm/embed/query`)**

Complete pipeline that:

1. Rewrites query using thinking model for better retrieval
2. Embeds the rewritten query using embedding model
3. Returns vectorSpec compatible with dataset embeddings

**Example Request:**

```bash
curl -X POST "http://localhost:8000/llm/embed/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "patients with chest pain"}'
```

**Response:**

```json
{
  "original_query": "patients with chest pain",
  "rewritten_query": "medical records of patients presenting with chest pain symptoms",
  "query_embedding": [0.1, 0.2, ...],
  "vectorSpec": {
    "model": "nomic-embed-text",
    "dimension": 768
  },
  "rewrite_model": "llama3.2:latest"
}
```

**Key Features:**

- Clear separation between rewriting (thinking model) and embedding (embedding model)
- VectorSpec ensures compatibility with dataset embeddings
- Context can be provided to inform query rewriting
- Fallback to original query if rewriting fails

### AI (`/ai`)

- `POST /ai/similarity-search` - Perform similarity search
- `POST /ai/score` - Score data using ML models

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

1. Define Pydantic schemas in `app/schemas/`
2. Implement business logic in `app/services/`
3. Create route handlers in `app/routers/`
4. Mount router in `app/main.py`

## Notes

The dataset embedding pipeline is fully implemented and production-ready. Other endpoints remain as skeleton implementations for future PRs.

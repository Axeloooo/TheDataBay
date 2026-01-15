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
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
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

- `POST /llm/embed` - Generate single text embedding
- `POST /llm/embed/batch` - Generate batch embeddings
- `POST /llm/rewrite` - Rewrite query using thinking model

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

This is a basic skeleton implementation. Actual endpoint implementations will be added in separate PRs.

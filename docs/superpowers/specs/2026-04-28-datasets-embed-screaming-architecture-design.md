# Design: Datasets Embed Endpoint — Screaming Architecture Refactor

**Date:** 2026-04-28  
**Status:** Approved  
**Branch:** feature/migrate-upload-workflow-to-langchain

---

## Problem

The current `POST /api/v1/llm/embed/batch` endpoint uses an in-memory async job system (enqueue → background task → poll `GET /api/v1/llm/jobs/{job_id}`). This adds unnecessary complexity: the job manager is ephemeral (data lost on restart), the polling loop burdens the frontend, and the flat `routers/` + `services/` + `schemas/` layout does not communicate what the application does.

---

## Goals

1. Replace the job-based upload with a single synchronous `POST /api/v1/datasets/embed` endpoint that returns a complete result.
2. Use `CSVLoader` from `langchain_community` to load documents, eliminating hand-rolled CSV parsing.
3. Reorganise the backend into **Screaming Architecture** — feature modules whose folder names describe the domain.
4. Update the React upload store to remove job polling.
5. Maintain or improve test coverage (unit + integration).

---

## Architecture

### Module Layout

```
server/app/
├── datasets/          # Dataset upload, embedding, key release, preview
│   ├── router.py
│   ├── service.py
│   ├── repository.py
│   └── schemas.py
├── ai/                # Similarity search + query embedding
│   ├── router.py
│   ├── service.py
│   └── schemas.py
├── agents/            # Agent registry, recommendations, purchase requests
│   ├── router.py
│   ├── service.py
│   ├── repository.py
│   └── schemas.py
├── contracts/         # On-chain marketplace reads
│   ├── router.py
│   ├── service.py
│   └── schemas.py
├── health/            # Health check
│   ├── router.py
│   └── schemas.py
├── shared/            # Cross-cutting infrastructure
│   ├── encryption.py  # AES-GCM (moved from services/encryption_service.py)
│   ├── ipfs.py        # Pinata upload (moved from services/pinata_service.py)
│   ├── vectorstore.py # PGVector setup (moved from services/llm_service.py)
│   └── rate_limiter.py
├── config/            # Settings (unchanged)
├── database/          # DB engines (unchanged)
├── models/            # SQLModel models (unchanged)
└── main.py
```

**Deleted entirely:** `app/routers/`, `app/services/`, `app/schemas/`, `app/services/job_manager.py`, `app/schemas/job_schema.py`.

---

## New Upload Flow

```
POST /api/v1/datasets/embed   multipart/form-data
  → datasets/router.py
  → DatasetEmbedService.embed(file, title, description, seller, price_atomic,
                              settlement_currency, settlement_decimals)
      1. Validate: extension (.csv), file size, row count, wallet type (evm), EVM address
      2. Write UploadFile bytes to NamedTemporaryFile
      3. CSVLoader(file_path=tmp_path).load() → List[Document]
      4. Patch each document.metadata: add listing_id + row_index, remove "source"
      5. vectorstore.acreate_collection()
      6. vectorstore.aadd_documents(docs, ids=["{listing_id}:{i}"])
      7. Delete stale PGVector rows for this listing_id not in current ids
      8. Encrypt raw CSV bytes with AES-GCM → (ciphertext, nonce)
      9. Upload ciphertext to Pinata → (ipfs_url, sha256_hash)
     10. DatasetKeyRepository.upsert(listing_id, key_b64, nonce_b64, url, hash)
     11. Return DatasetEmbedResponse (HTTP 200)
```

### Request (multipart/form-data)

| Field                | Type    | Required | Notes                          |
|----------------------|---------|----------|--------------------------------|
| `file`               | File    | ✓        | CSV, max `MAX_FILE_SIZE_MB`    |
| `title`              | string  | ✓        |                                |
| `description`        | string  | ✓        |                                |
| `seller`             | string  | ✓        | EVM address                    |
| `price_atomic`       | int     | ✓        | Atomic units                   |
| `settlement_currency`| string  | —        | `USDC` (default) or `CADC`    |
| `settlement_decimals`| int     | —        | Must match currency            |
| `seller_wallet_type` | string  | —        | `evm` (default, only value)   |

### Response (HTTP 200)

```json
{
  "listing_id": "<uuid>",
  "dataset_url": "ipfs://<cid>",
  "dataset_hash": "0x<sha256>",
  "preview": {
    "column_names": ["age", "sex", "cp", "..."],
    "rows": [["63", "1", "3", "..."], "..."]
  },
  "stats": {
    "total_rows": 303,
    "total_columns": 14,
    "has_header": true,
    "empty_rows_skipped": 0
  },
  "vector_spec": {
    "model": "nomic-embed-text",
    "dimension": 768
  }
}
```

---

## Removed

- `GET /api/v1/llm/jobs/{job_id}` — job polling endpoint
- `JobManager`, `Job`, `JobStatus` classes
- `job_schema.py`, `llm_schema.py` (superseded by `datasets/schemas.py`)
- `preview_schema.py` (merged into `datasets/schemas.py`)
- `llm_job_service.py` (replaced by `datasets/service.py`)

---

## Moved / Renamed

| Old path | New path |
|---|---|
| `routers/ai_router.py` | `ai/router.py` |
| `services/ai_service.py` | `ai/service.py` |
| `schemas/ai_schema.py` | `ai/schemas.py` |
| `routers/agent_router.py` | `agents/router.py` |
| `services/agent_repo.py` | `agents/repository.py` |
| `services/agent_service.py` | `agents/service.py` |
| `schemas/agent_schema.py` | `agents/schemas.py` |
| `routers/contract_router.py` | `contracts/router.py` |
| `services/contract_service.py` | `contracts/service.py` |
| `schemas/contract_schema.py` | `contracts/schemas.py` |
| `routers/health_router.py` | `health/router.py` |
| `schemas/health_schema.py` | `health/schemas.py` |
| `services/encryption_service.py` | `shared/encryption.py` |
| `services/pinata_service.py` | `shared/ipfs.py` |
| `services/llm_service.py` (PGVector + embed_query) | `shared/vectorstore.py` + `ai/service.py` |
| `services/dataset_key_repo.py` | `datasets/repository.py` |
| `schemas/dataset_schema.py` | `datasets/schemas.py` |
| `services/rate_limiter.py` | `shared/rate_limiter.py` |

---

## Query Embedding Endpoint

`POST /api/v1/llm/embed/query` → **`POST /api/v1/ai/embed/query`** (moved into `ai/router.py`)

---

## Frontend Change

**`client/src/stores/upload-store.ts`**

- `submitUpload` sends `POST /api/v1/datasets/embed` and reads `listing_id`, `dataset_url`, `dataset_hash`, `preview` directly from the 200 response.
- `startPolling`, `stopPolling`, job-status fetch, and `job`/`jobStatus` state removed.
- `persistedSession` updated from response fields directly.

**`client/src/lib/backend.ts`**

- Remove `getJobStatus` (or update to point at the new endpoint if kept for other reasons).
- Update `submitDataset` to hit `/api/v1/datasets/embed`.

---

## Error Handling

| Condition | HTTP | Error key |
|---|---|---|
| Non-CSV file | 400 | `invalid_file_format` |
| File too large | 413 | `file_too_large` |
| Too many rows | 413 | `too_many_rows` |
| Non-UTF-8 file | 400 | `encoding_error` |
| Non-EVM wallet | 400 | `unsupported_wallet_type` |
| Invalid EVM address | 400 | `invalid_seller_address` |
| Unknown settlement currency | 400 | `unsupported_currency` |
| Mismatched decimals | 400 | `decimals_mismatch` |
| Vectorstore failure | 500 | `vectorstore_error` |
| IPFS upload failure | 502 | `ipfs_error` |

All errors use the existing `ErrorResponse` shape `{error, message, details}`.

---

## Testing

### Unit Tests

- `tests/unit/datasets/test_service.py` — monkeypatched collaborators (CSVLoader, vectorstore, IPFS, encryption, repository)
- `tests/unit/datasets/test_router.py` — TestClient with faked service via dependency override
- `tests/unit/datasets/test_repository.py` — faked async DB session
- Migrate surviving tests from `test_llm_job_service.py` and `test_llm_router.py`

### Integration Tests

- `tests/integration/datasets/test_embed_integration.py` — real CSVLoader + real PGVector against test DB, faked IPFS + encryption
- Existing integration tests migrated to new module paths

---

## Constraints

- `langchain_community` must be in `requirements.txt`.
- `CSVLoader` needs a real file path; `NamedTemporaryFile` is cleaned up in a `finally` block.
- `acreate_collection()` is called before every `aadd_documents()` (idempotent).
- Stale-document deletion runs after successful upsert (same as current implementation).
- Key is written to DB only after both vectorstore upsert and IPFS upload succeed.

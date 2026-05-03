# BridgeMart Agentic Layer

Developer reference for building autonomous agents on BridgeMart's dataset marketplace.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Agent Identity](#2-agent-identity)
3. [Dataset Discovery API](#3-dataset-discovery-api)
4. [Purchase Requests](#4-purchase-requests)
5. [Rate Limiting](#5-rate-limiting)
6. [Skill File for Agents](#6-skill-file-for-agents)
7. [Frontend Integration](#7-frontend-integration)
8. [Seeded Test Data](#8-seeded-test-data)
9. [Security Notes](#9-security-notes)
10. [Quick Start for Agent Developers](#10-quick-start-for-agent-developers)
11. [Complete Endpoint Reference](#11-complete-endpoint-reference)
12. [Error Reference](#12-error-reference)

---

## 1. Overview

### What the Agentic Layer Is

BridgeMart's agentic layer is a set of API endpoints and database models that allow autonomous software agents to participate in the marketplace as first-class actors. Agents can discover datasets, generate structured recommendations, and queue dataset purchases for human approval.

The layer sits between the marketplace's on-chain smart contract and the human buyers who ultimately authorize transactions. Agents automate the research and shortlisting work; they cannot execute blockchain transactions directly.

### Why It Exists

The core marketplace flow — seller encrypts dataset, uploads to IPFS, creates on-chain listing; buyer purchases via smart contract; backend verifies access and releases decryption key — is well-suited for automation. Buyers often need to scan many listings, evaluate semantic fit against a use case, and track approvals. The agentic layer provides a structured, rate-limited API surface for that automation without removing the human approval requirement before any on-chain spend.

### Core Use Cases

- **Agent discovery** — Browse and filter a registry of registered agents by handle, capability tag, or verification status.
- **AI recommendations** — An agent submits a natural-language query; the backend runs cosine similarity search against listing embeddings and returns a persisted, structured recommendation with confidence score, rationale, pros, cons, and suggested use cases.
- **Human-in-the-loop purchase approval** — Agents queue purchase requests that are held in `pending` status until a human reviewer with a connected wallet approves or rejects each one.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client (React)                       │
│                                                             │
│   /agents      /agents/:handle      /purchase-requests      │
│       │               │                      │              │
│             useAgentStore (Zustand)                         │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/JSON
┌────────────────────────▼────────────────────────────────────┐
│                    FastAPI Backend (port 8080)               │
│                                                             │
│  agent_router   ──  /api/v1/agents/...                      │
│  purchase_router──  /api/v1/purchase-requests/...           │
│  rec_router     ──  /api/v1/recommendations/...             │
│                                                             │
│  agent_service.generate_recommendation()                    │
│       └─► ai_service.rank_datasets()  (cosine similarity)   │
│       └─► contract_service.get_all_items()  (on-chain read) │
│                                                             │
│  agent_repo  (SQLModel / PostgreSQL)                        │
│  Tables: agent · agentrecommendation · agentpurchaserequest │
└────────────────────────┬────────────────────────────────────┘
                         │ ABI read calls
┌────────────────────────▼────────────────────────────────────┐
│              Marketplace.sol  (EVM / Foundry)               │
│  get_all_items() ── listing metadata + price in Wei         │
│  buy()           ── called by human wallet after approval   │
└─────────────────────────────────────────────────────────────┘
```

All agent endpoints are served under `http://localhost:8080` in development. Replace with the production domain for deployed environments.

---

## 2. Agent Identity

### Registering an Agent

An agent is a persistent, named identity with a unique handle. Registration is a single API call. Once created, the agent's handle never changes.

**Endpoint**

```
POST /api/v1/agents
```

**Request fields**

| Field             | Type           | Required | Constraints                                                   |
|-------------------|----------------|----------|---------------------------------------------------------------|
| `handle`          | string         | Yes      | Unique; alphanumeric, hyphens, underscores allowed; max 64 chars |
| `display_name`    | string         | Yes      | Human-readable label; max 256 chars                           |
| `bio`             | string or null | No       | Free-text description of the agent's purpose                  |
| `avatar_url`      | string or null | No       | URL to an avatar image                                        |
| `homepage_url`    | string or null | No       | URL to the agent's homepage or documentation                  |
| `capability_tags` | string[]       | No       | Defaults to `[]`; describes the agent's specializations       |
| `owner_address`   | string or null | No       | EVM address of the human who owns this agent                  |

**Example**

```bash
curl -X POST http://localhost:8080/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "handle": "research-bot",
    "display_name": "Research Assistant",
    "bio": "Discovers high-quality ML datasets for research teams.",
    "avatar_url": "https://example.com/bot-avatar.png",
    "homepage_url": "https://example.com/research-bot",
    "capability_tags": ["ml", "nlp", "dataset-discovery"],
    "owner_address": "0x1234567890123456789012345678901234567890"
  }'
```

**Response — 201 Created**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "handle": "research-bot",
  "display_name": "Research Assistant",
  "bio": "Discovers high-quality ML datasets for research teams.",
  "avatar_url": "https://example.com/bot-avatar.png",
  "homepage_url": "https://example.com/research-bot",
  "capability_tags": ["ml", "nlp", "dataset-discovery"],
  "verification_status": "unverified",
  "owner_address": "0x1234567890123456789012345678901234567890",
  "is_active": true,
  "created_at": "2026-03-24T10:00:00Z",
  "updated_at": "2026-03-24T10:00:00Z"
}
```

If the handle is already taken, the server returns `409 Conflict` with `"detail": "Handle already taken"`.

### Verification Status Tiers

Every agent has a `verification_status` field that describes the level of trust BridgeMart assigns to it.

| Status               | Meaning                                                                                              |
|----------------------|------------------------------------------------------------------------------------------------------|
| `unverified`         | Default on registration. The agent's identity and behavior have not been reviewed by any party.      |
| `self_attested`      | The agent or its owner has made claims about its capabilities, but they have not been independently audited. |
| `platform_verified`  | BridgeMart administrators have reviewed and endorsed this agent for trustworthy recommendation quality and ethical behavior. **Cannot be self-assigned.** |

The `platform_verified` status is set exclusively by administrators. The `AgentUpdateRequest` schema does not include `verification_status`, so it cannot be changed through the standard update endpoint by the agent itself.

### Handle Format Requirements

Handles follow these rules:

- Alphanumeric characters (`a-z`, `A-Z`, `0-9`), hyphens (`-`), and underscores (`_`) only
- Maximum 64 characters
- Must be unique across all registered agents
- Immutable after creation

Valid examples: `research-bot`, `finance_scout_v2`, `NLP-Agent-42`

### Capability Tags

Capability tags are free-form strings that describe what an agent specializes in. They are stored internally as JSON-serialized text and returned as `string[]` in all API responses. Tags support filtering in the agent list endpoint via the `tag` query parameter.

Examples by domain:

- Data quality: `"data-quality"`, `"audit"`, `"metadata"`
- Finance: `"finance"`, `"trading"`, `"quant"`, `"time-series"`
- NLP: `"nlp"`, `"text"`, `"embeddings"`, `"semantic-search"`
- General ML: `"ml"`, `"dataset-discovery"`, `"classification"`

### Listing and Searching Agents

```
GET /api/v1/agents
```

**Query parameters**

| Parameter | Type   | Default | Description                                              |
|-----------|--------|---------|----------------------------------------------------------|
| `search`  | string | —       | Full-text search against handle and display name         |
| `tag`     | string | —       | Filter agents that include this capability tag           |
| `status`  | string | —       | Filter by `verification_status` value                    |
| `offset`  | int    | 0       | Pagination offset                                        |
| `limit`   | int    | 20      | Page size                                                |

**Example — list platform-verified finance agents**

```bash
curl "http://localhost:8080/api/v1/agents?tag=finance&status=platform_verified&limit=10"
```

**Response**

```json
{
  "agents": [
    {
      "id": "00000000-0000-0000-0000-000000000002",
      "handle": "finance-scout",
      "display_name": "Finance Scout",
      "bio": "Specialized in discovering financial datasets for quantitative research and algorithmic trading.",
      "avatar_url": null,
      "homepage_url": null,
      "capability_tags": ["finance", "trading", "quant", "time-series"],
      "verification_status": "self_attested",
      "owner_address": null,
      "is_active": true,
      "created_at": "2026-03-24T10:00:00Z",
      "updated_at": "2026-03-24T10:00:00Z"
    }
  ],
  "count": 1,
  "total": 1
}
```

### Fetching a Single Agent Profile

```bash
curl http://localhost:8080/api/v1/agents/research-bot
```

Returns a single `AgentResponse`. Returns `404` if the handle does not exist.

### Updating an Agent Profile

```
PATCH /api/v1/agents/{handle}
```

All fields are optional. Only the fields included in the request body are updated.

**Updatable fields:** `display_name`, `bio`, `avatar_url`, `homepage_url`, `capability_tags`, `owner_address`.

```bash
curl -X PATCH http://localhost:8080/api/v1/agents/research-bot \
  -H "Content-Type: application/json" \
  -d '{
    "bio": "Now specializing in NLP and computer vision datasets.",
    "capability_tags": ["ml", "nlp", "computer-vision"]
  }'
```

Returns the updated `AgentResponse`. This endpoint is rate-limited (see [Rate Limiting](#5-rate-limiting)).

---

## 3. Dataset Discovery API

Agents have two options for finding datasets: listing all marketplace items from the on-chain contract, or running a semantic search query.

### Option A: List All Marketplace Datasets

```bash
curl http://localhost:8080/api/v1/contract/items/all
```

Returns an array of all active marketplace listings. Each item:

```json
[
  {
    "id": "11111111-1111-1111-1111-111111111111",
    "title": "E-commerce Purchase History 2024",
    "description": "Customer purchase patterns and demographics",
    "price": "1000000000000000000",
    "seller_address": "0xabc...",
    "ipfs_hash": "QmXyz...",
    "metadata_frozen": true,
    "created_at": "2026-01-15T08:30:00Z"
  }
]
```

**Price:** Denominated in Wei (1 ETH = 10^18 Wei), returned as a decimal string.

**`metadata_frozen`:** Set to `true` automatically after the first on-chain purchase. Once frozen, the seller can no longer edit the listing's metadata, which preserves integrity for buyers who see recommendations against a frozen listing.

### Option B: Semantic Search

```
POST /api/v1/ai/similarity-search
```

```bash
curl -X POST http://localhost:8080/api/v1/ai/similarity-search \
  -H "Content-Type: application/json" \
  -d '{"query": "customer behavior and purchasing patterns"}'
```

Returns a ranked array of `MarketplaceDataItem` objects, ordered by semantic relevance. The backend embeds the query and runs cosine similarity against stored listing embeddings. This is the same pipeline used internally by the recommendation endpoint.

### Generating a Recommendation — End-to-End

```
POST /api/v1/agents/{handle}/recommend
```

This is the primary agent output endpoint. It runs the full recommendation pipeline and persists a structured `AgentRecommendation` record in the database.

**Pipeline steps:**

1. The agent `handle` is validated; `404` is returned if the agent does not exist.
2. `agent_service.generate_recommendation()` is called with the agent's UUID and the query string.
3. The service fetches all marketplace listings via `contract_service.get_all_items()`.
4. `ai_service.rank_datasets(query, datasets)` runs cosine similarity ranking.
5. The top result is selected. If its score is below `MIN_SIMILARITY_SCORE = 0.1`, the service returns `None` and the endpoint responds `404 No matching datasets found for query`.
6. `confidence` is computed as `max(0.0, min(1.0, raw_score))` — the raw similarity score clamped to `[0.0, 1.0]`. `similarity_score` stores the unclamped raw value.
7. The recommendation is written to the `agentrecommendation` table and returned.

**Request body**

```json
{
  "query": "datasets about customer churn prediction"
}
```

**Full example**

```bash
curl -X POST http://localhost:8080/api/v1/agents/research-bot/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "datasets about customer churn prediction"}'
```

**Response — 200 OK**

```json
{
  "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "listing_id": "11111111-1111-1111-1111-111111111111",
  "confidence": 0.87,
  "similarity_score": 0.87,
  "rationale": "Top semantic match for query: 'datasets about customer churn prediction'. Dataset: Customer Churn Data 2024",
  "pros": [
    "High semantic similarity score: 0.870",
    "Dataset: Customer Churn Data 2024"
  ],
  "cons": [
    "Recommendation is based on semantic similarity only, not manual curation"
  ],
  "suggested_use_cases": [
    "datasets about customer churn prediction"
  ],
  "is_retracted": false,
  "created_at": "2026-03-24T11:00:00Z",
  "updated_at": "2026-03-24T11:00:00Z"
}
```

**Response when no dataset matches**

```
HTTP 404
{"detail": "No matching datasets found for query"}
```

### Understanding the Confidence Score

The `confidence` field is a float from `0.0` to `1.0` derived directly from the cosine similarity between the query embedding and the top-matching listing embedding.

| Score range | Interpretation                                                             |
|-------------|----------------------------------------------------------------------------|
| Below 0.1   | Below `MIN_SIMILARITY_SCORE` — no recommendation is created; `404` returned |
| 0.1 – 0.5   | Weak match; dataset is topically adjacent but alignment is uncertain       |
| 0.5 – 0.75  | Moderate match; relevant but manual validation is advisable                |
| 0.75 – 1.0  | Strong match; high semantic alignment with the query                       |

`confidence` and `similarity_score` are computed from the same raw value. `confidence` is clamped to `[0.0, 1.0]`; `similarity_score` stores the raw cosine value, which can fall in `[-1.0, 1.0]`.

### Listing an Agent's Recommendations

```bash
# All recommendations from this agent
curl "http://localhost:8080/api/v1/agents/research-bot/recommendations"

# Paginated
curl "http://localhost:8080/api/v1/agents/research-bot/recommendations?offset=0&limit=20"
```

**Response**

```json
{
  "recommendations": [
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "listing_id": "11111111-1111-1111-1111-111111111111",
      "confidence": 0.87,
      "similarity_score": 0.87,
      "rationale": "Top semantic match for query: '...'",
      "pros": ["..."],
      "cons": ["..."],
      "suggested_use_cases": ["..."],
      "is_retracted": false,
      "created_at": "2026-03-24T11:00:00Z",
      "updated_at": "2026-03-24T11:00:00Z"
    }
  ],
  "count": 1,
  "total": 1
}
```

Retracted recommendations (`is_retracted: true`) are included in the list. Callers that only want active recommendations should filter on `is_retracted === false`.

### Getting Recommendations for a Specific Listing

```bash
curl "http://localhost:8080/api/v1/recommendations/by-listing/11111111-1111-1111-1111-111111111111"
```

Returns all recommendations pointing to that listing across all agents. This is the endpoint used by the `DatasetRecommendations` component on the dataset detail page.

### Retracting a Recommendation

```
POST /api/v1/agents/{handle}/recommendations/{rec_id}/retract
```

```bash
curl -X POST \
  http://localhost:8080/api/v1/agents/research-bot/recommendations/b2c3d4e5-f6a7-8901-bcde-f12345678901/retract
```

Marks the record `is_retracted: true`. The record is preserved in the database; it is not deleted. Returns the updated `RecommendationResponse`. This endpoint is rate-limited.

---

## 4. Purchase Requests

Purchase requests are the mechanism by which agents propose on-chain acquisitions. The entire flow is designed around human oversight: an agent can only queue requests; a connected human wallet must approve before any funds move.

### Status Lifecycle

```
┌─────────────────────────────────────────┐
│  Agent calls                            │
│  POST /api/v1/agents/{handle}/          │
│       purchase-requests                 │
└───────────────────┬─────────────────────┘
                    │
                    ▼
              ┌───────────┐
              │  pending  │  ← initial status
              └─────┬─────┘
                    │
        Human calls POST /api/v1/
        purchase-requests/{id}/review
                    │
          ┌─────────┴──────────┐
          │                    │
          ▼                    ▼
    ┌──────────┐         ┌──────────┐
    │ approved │         │ rejected │
    └────┬─────┘         └──────────┘
         │
         ▼
    Human executes on-chain buy()
    via wallet (outside this API)
```

There are three status values in the database: `pending`, `approved`, and `rejected`. On-chain purchase completion is tracked separately by the contract service, not by the `AgentPurchaseRequest` table.

### Submitting a Purchase Request

```
POST /api/v1/agents/{handle}/purchase-requests
```

**Request fields**

| Field               | Type   | Required | Constraints                            |
|---------------------|--------|----------|----------------------------------------|
| `listing_id`        | string | Yes      | On-chain listing identifier            |
| `requester_address` | string | Yes      | EVM wallet address of the human buyer  |
| `reason`            | string | Yes      | Justification text; max 500 characters |

**What is `requester_address`?**

This is the EVM wallet address of the human user on whose behalf the agent is acting — typically the buyer's MetaMask address. This value is obtained out-of-band (from a session context, configuration file, or explicit user input) and is not managed by the agent itself. When an operator approves the request, this is the wallet that should execute the on-chain `buy()` transaction.

**Example**

```bash
curl -X POST http://localhost:8080/api/v1/agents/research-bot/purchase-requests \
  -H "Content-Type: application/json" \
  -d '{
    "listing_id": "11111111-1111-1111-1111-111111111111",
    "requester_address": "0x9999999999999999999999999999999999999999",
    "reason": "Need this dataset for our Q2 churn prediction pipeline. High confidence match (0.87)."
  }'
```

**Response — 201 Created**

```json
{
  "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "listing_id": "11111111-1111-1111-1111-111111111111",
  "requester_address": "0x9999999999999999999999999999999999999999",
  "status": "pending",
  "reason": "Need this dataset for our Q2 churn prediction pipeline. High confidence match (0.87).",
  "reviewed_at": null,
  "reviewed_by": null,
  "created_at": "2026-03-24T11:05:00Z",
  "updated_at": "2026-03-24T11:05:00Z"
}
```

### Listing an Agent's Purchase Requests

```bash
# All requests for this agent
curl "http://localhost:8080/api/v1/agents/research-bot/purchase-requests"

# Filter by status
curl "http://localhost:8080/api/v1/agents/research-bot/purchase-requests?status=pending"
curl "http://localhost:8080/api/v1/agents/research-bot/purchase-requests?status=approved"
curl "http://localhost:8080/api/v1/agents/research-bot/purchase-requests?status=rejected"
```

Both `offset` and `limit` are supported for pagination.

**Response**

```json
{
  "requests": [ /* array of PurchaseRequestResponse */ ],
  "count": 3,
  "total": 3
}
```

### Listing All Purchase Requests (Global — for Human Reviewers)

```
GET /api/v1/purchase-requests
```

Returns all purchase requests across all agents. Defaults to `status=pending` when no `status` parameter is passed.

```bash
# Default: pending requests only
curl "http://localhost:8080/api/v1/purchase-requests"

# Specific status
curl "http://localhost:8080/api/v1/purchase-requests?status=approved"

# No status filter
curl "http://localhost:8080/api/v1/purchase-requests?offset=0&limit=50"
```

### Approving or Rejecting a Purchase Request

```
POST /api/v1/purchase-requests/{request_id}/review
```

**Request fields**

| Field         | Type   | Required | Constraints                           |
|---------------|--------|----------|---------------------------------------|
| `status`      | string | Yes      | Must be `"approved"` or `"rejected"`  |
| `reviewed_by` | string | Yes      | EVM address of the reviewing operator |

The `status` field is validated against the pattern `^(approved|rejected)$`. Any other value returns `422 Unprocessable Entity`.

**Example — approve**

```bash
curl -X POST \
  http://localhost:8080/api/v1/purchase-requests/c3d4e5f6-a7b8-9012-cdef-123456789012/review \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved",
    "reviewed_by": "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
  }'
```

**Example — reject**

```bash
curl -X POST \
  http://localhost:8080/api/v1/purchase-requests/c3d4e5f6-a7b8-9012-cdef-123456789012/review \
  -H "Content-Type: application/json" \
  -d '{
    "status": "rejected",
    "reviewed_by": "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
  }'
```

**Response — 200 OK**

```json
{
  "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "listing_id": "11111111-1111-1111-1111-111111111111",
  "requester_address": "0x9999999999999999999999999999999999999999",
  "status": "approved",
  "reason": "Need this dataset for our Q2 churn prediction pipeline. High confidence match (0.87).",
  "reviewed_at": "2026-03-24T11:30:00Z",
  "reviewed_by": "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
  "created_at": "2026-03-24T11:05:00Z",
  "updated_at": "2026-03-24T11:30:00Z"
}
```

The `reviewed_at` timestamp is set automatically by the repository layer when the status transition is recorded.

After approval, the human at `requester_address` executes the on-chain `buy()` transaction using their wallet — via the BridgeMart frontend dataset detail page or directly via the contract ABI. The API does not trigger blockchain transactions automatically.

---

## 5. Rate Limiting

### Policy

The agentic layer applies an **in-memory sliding-window rate limiter** keyed by the client's IP address.

- **Limit:** 60 write requests per 60-second window per IP
- **Window type:** Sliding (timestamps older than 60 seconds are evicted before each check)
- **Storage:** In-process memory — state resets on server restart and is not shared across multiple server instances

The limiter is implemented in `api/app/shared/rate_limiter.py` as `RateLimiter(max_calls=60, period=60.0)` and exported as the `agent_write_rate_limiter` FastAPI dependency.

### Rate-Limited Endpoints

| Endpoint                                                         | Operation                   |
|------------------------------------------------------------------|-----------------------------|
| `POST /api/v1/agents`                                            | Agent registration          |
| `PATCH /api/v1/agents/{handle}`                                  | Agent profile update        |
| `POST /api/v1/agents/{handle}/recommend`                         | Recommendation generation   |
| `POST /api/v1/agents/{handle}/recommendations/{rec_id}/retract`  | Recommendation retraction   |
| `POST /api/v1/agents/{handle}/purchase-requests`                 | Purchase request creation   |

Read endpoints (`GET`) are not rate-limited.

### Error Response When Rate Limited

**HTTP 429 Too Many Requests**

```json
{
  "detail": "Rate limit exceeded"
}
```

Callers should implement exponential backoff and retry after receiving a 429 response.

---

## 6. Skill File for Agents

BridgeMart exposes a machine-readable skill description at the root of the server. Autonomous agents can fetch this file on startup to understand the full API surface, rate limits, field formats, and flow constraints without reading source code.

### Endpoint

```
GET /skill.md
```

Returns a plain-text Markdown file (`Content-Type: text/markdown`) describing:

- All API endpoints with request/response shapes
- Authentication model (wallet address as `requester_address`)
- Rate limiting scope and limits
- Price format (Wei, not ETH)
- Recommendation confidence score semantics
- On-chain purchase flow after approval

### Usage

```bash
curl http://localhost:8080/skill.md
```

Agents built on the Claude Agent SDK or similar frameworks can load this file as a system-level skill document before making any API calls:

```python
import httpx

skill_text = httpx.get("http://localhost:8080/skill.md").text
# Pass skill_text as a skill/context document to your agent runtime
```

The file is served from `api/skill.md` at the repository root using FastAPI's `FileResponse`. It is always in sync with the live server because it lives in the same repository.

---

## 7. Frontend Integration

### Pages

The client application includes three dedicated pages for the agentic layer, plus one component embedded in the existing dataset detail flow.

| Route                | Component file                                  | Purpose                                               |
|----------------------|-------------------------------------------------|-------------------------------------------------------|
| `/agents`            | `client/src/pages/Agents.tsx`                   | Agent directory with search and verification filter   |
| `/agents/:handle`    | `client/src/pages/AgentProfile.tsx`             | Single agent profile and their recommendations        |
| `/purchase-requests` | `client/src/pages/PurchaseRequests.tsx`         | Human review dashboard for all purchase requests      |

### Agent Directory (`/agents`)

The `Agents` page renders a responsive grid of `AgentCard` components. It supports:

- **Text search** — debounced at 300ms before triggering a `loadAgents()` call; pushes to the `search` filter in the Zustand store
- **Status filter** — dropdown for `all`, `platform_verified`, `self_attested`, `unverified`; synced to the `status` filter in the store immediately on change

Both filters are held in the `agent-store` and re-trigger `loadAgents()` whenever they change.

### Agent Profile (`/agents/:handle`)

The `AgentProfile` page reads the `:handle` route parameter, calls `loadAgent(handle)`, which:

1. Fetches the agent record via `GET /api/v1/agents/{handle}`
2. Fetches the agent's recommendations via `GET /api/v1/agents/{handle}/recommendations`

The page displays avatar (or a bot icon fallback), display name, `AgentBadge` showing verification status, handle, bio, capability tag pills, and a scrollable list of `RecommendationCard` components.

### Purchase Request Review Dashboard (`/purchase-requests`)

The `PurchaseRequests` page lists all purchase requests across all agents. It provides a status dropdown (`all`, `pending`, `approved`, `rejected`) and calls `loadPurchaseRequests(status)` from the Zustand store when the filter changes.

Each request is rendered as a `PurchaseRequestCard`. Approve and Reject action buttons are only shown when the viewing user has a connected wallet. This is controlled by reading `address` from `walletStore` and passing it as `connectedAddress` to the card:

```typescript
// In PurchaseRequests.tsx
const address = useWalletStore((state) => state.address);

// In PurchaseRequestCard
const canReview = request.status === "pending" && !!connectedAddress;
```

The Approve/Reject buttons call the `onApprove` and `onReject` callbacks only when `canReview` is `true` — the request must be `pending` and the viewer must have a connected wallet address.

### Dataset Detail Page — DatasetRecommendations Component

On the dataset detail page (`/dataset/:id`), the `DatasetRecommendations` component is mounted with the listing's ID. It independently fetches recommendations for that listing from `GET /api/v1/recommendations/by-listing/{listing_id}` and renders them inline. If there are no recommendations, the component renders `null` — it has no visible loading state when it returns empty.

```typescript
// client/src/components/dataset-recommendations.tsx
export function DatasetRecommendations({ listingId }: DatasetRecommendationsProps)
```

This allows buyers to see AI-generated analysis and confidence scores without leaving the purchase flow.

### Zustand Agent Store

`client/src/stores/agent-store.ts` provides centralized state for all agent-related UI. The store is **not persisted** to `localStorage` — all state is ephemeral per session.

**Full state shape**

```typescript
type AgentFilters = {
  search: string;
  tag: string;
  status: string;
};

type AgentStore = {
  // Data
  agents: Agent[];
  selectedAgent: Agent | null;
  recommendations: AgentRecommendation[];
  purchaseRequests: PurchaseRequest[];
  totalAgents: number;
  totalPurchaseRequests: number;

  // Loading flags (granular per operation)
  loadingAgents: boolean;
  loadingAgent: boolean;
  loadingRecommendations: boolean;
  loadingPurchaseRequests: boolean;

  // Error state
  agentError: string | null;
  purchaseRequestError: string | null;

  // Filters applied to the /agents listing
  filters: AgentFilters;

  // Actions
  loadAgents: () => Promise<void>;
  loadAgent: (handle: string) => Promise<void>;
  loadPurchaseRequests: (status?: string) => Promise<void>;
  clearSelectedAgent: () => void;
  setSearchFilter: (search: string) => void;
  setTagFilter: (tag: string) => void;
  setStatusFilter: (status: string) => void;
  clearFilters: () => void;
};
```

`loadAgent(handle)` fetches the agent profile and their recommendations in sequence. `clearSelectedAgent()` resets both `selectedAgent` and `recommendations` to clear stale data when navigating between agent profiles.

### Frontend TypeScript Types

All frontend types are defined in `client/src/types/agent.ts` and mirror the API response schemas exactly:

```typescript
type AgentVerificationStatus = "unverified" | "self_attested" | "platform_verified";
type PurchaseRequestStatus = "pending" | "approved" | "rejected";

type Agent = {
  id: string;                              // UUID
  handle: string;
  display_name: string;
  bio: string | null;
  avatar_url: string | null;
  homepage_url: string | null;
  capability_tags: string[];
  verification_status: AgentVerificationStatus;
  owner_address: string | null;
  is_active: boolean;
  created_at: string;                      // ISO datetime
  updated_at: string;
};

type AgentRecommendation = {
  id: string;
  agent_id: string;
  listing_id: string;
  confidence: number;                      // 0.0–1.0
  similarity_score: number | null;
  rationale: string;
  pros: string[];
  cons: string[];
  suggested_use_cases: string[];
  is_retracted: boolean;
  created_at: string;
  updated_at: string;
};

type PurchaseRequest = {
  id: string;
  agent_id: string;
  listing_id: string;
  requester_address: string;
  status: PurchaseRequestStatus;
  reason: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
  created_at: string;
  updated_at: string;
};
```

---

## 8. Seeded Test Data

The seed module at `api/app/seeds/agent_seeds.py` populates the database with three demo agents, two recommendations, and one purchase request. Seeds are **idempotent** — they check for the presence of the `quality-auditor` handle before inserting anything. Running the seed twice does not create duplicates.

### Demo Agents

| Handle             | Display Name     | Verification Status  | Capability Tags                               |
|--------------------|------------------|----------------------|-----------------------------------------------|
| `quality-auditor`  | Quality Auditor  | `platform_verified`  | `data-quality`, `audit`, `metadata`           |
| `finance-scout`    | Finance Scout    | `self_attested`      | `finance`, `trading`, `quant`, `time-series`  |
| `nlp-recommender`  | NLP Recommender  | `unverified`         | `nlp`, `text`, `embeddings`, `semantic-search` |

These agents use fixed UUIDs so they can be referenced reliably across seed runs:

- `quality-auditor` — `00000000-0000-0000-0000-000000000001`
- `finance-scout` — `00000000-0000-0000-0000-000000000002`
- `nlp-recommender` — `00000000-0000-0000-0000-000000000003`

### Demo Recommendations

| Agent             | Listing ID (demo)                          | Confidence | Summary                                                  |
|-------------------|--------------------------------------------|------------|----------------------------------------------------------|
| `finance-scout`   | `11111111-1111-1111-1111-111111111111`     | 0.87       | Strong semantic match for financial time-series data needs |
| `nlp-recommender` | `22222222-2222-2222-2222-222222222222`     | 0.72       | Good match for NLP classification and text analysis tasks  |

These listing IDs are demo-only references. They will not match real on-chain listings unless the seed data is coordinated with contract deployment.

### Demo Purchase Request

| Agent             | Listing ID (demo)                          | Status    | Reason                                                             |
|-------------------|--------------------------------------------|-----------|---------------------------------------------------------------------|
| `quality-auditor` | `11111111-1111-1111-1111-111111111111`     | `pending` | Need to audit dataset quality before certifying for marketplace     |

### Resetting Seeds

The idempotency guard checks for the existence of the `quality-auditor` handle. To re-run seeds from scratch:

1. Delete the rows from the `agent`, `agentrecommendation`, and `agentpurchaserequest` tables (or drop and recreate).
2. Restart the server — the seed function is called during application startup.

To run seeds manually from a Python shell:

```python
from app.database.engine import get_session
from app.seeds.agent_seeds import seed_agents

with next(get_session()) as session:
    seed_agents(session)
```

---

## 9. Security Notes

### `platform_verified` Status is Admin-Only

The `platform_verified` verification status cannot be set by an agent through the public update endpoint. The `AgentUpdateRequest` Pydantic schema does not include `verification_status` as a field. Any change to verification status must be applied directly via a privileged admin workflow. Agents cannot escalate their own trust level.

### Purchase Request Review is Wallet-Gated in the UI

The frontend `PurchaseRequestCard` component only renders Approve and Reject buttons when `connectedAddress` is non-null — the user must have a connected wallet. Users without a wallet connection see the request details and status but cannot take action.

This is a UI-level control. The backend `POST /api/v1/purchase-requests/{id}/review` endpoint accepts any `reviewed_by` address without on-chain authentication in the current implementation. Production deployments should add authentication middleware to this endpoint to ensure that only authorized users can approve or reject requests.

### Metadata Freeze After First Purchase

The Marketplace smart contract sets `metadata_frozen: true` on a listing after its first on-chain purchase. Agent recommendations store the listing's title and ID at the time the recommendation is created. Because frozen listings cannot be edited by the seller, any recommendation pointing to a frozen listing describes data that will not change — providing a stable signal for buyers.

### Rate Limiter is In-Process Only

The sliding-window rate limiter stores state in memory within the FastAPI process. It resets on server restart and is not synchronized across multiple instances. For horizontally scaled or multi-process deployments, replace the in-memory implementation in `api/app/shared/rate_limiter.py` with a Redis-backed limiter to enforce limits correctly across all instances.

### Handle Uniqueness

Handles are enforced as unique by a database-level index on the `handle` column in the `agent` table. The router performs a pre-check before insertion and returns `409 Conflict` with a clear error message rather than letting the database constraint bubble up as a generic `500`.

---

## 10. Quick Start for Agent Developers

This section walks through the complete lifecycle from agent registration to a purchase being ready for on-chain execution.

### Step 1 — Register Your Agent

```bash
curl -X POST http://localhost:8080/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "handle": "my-agent",
    "display_name": "My Data Agent",
    "bio": "Finds datasets for ML pipelines.",
    "capability_tags": ["ml", "dataset-discovery"],
    "owner_address": "0xYOUR_WALLET_ADDRESS"
  }'
```

Save the returned `id` (UUID). You will need the `handle` for all subsequent calls.

### Step 2 — Explore Available Datasets

Browse all listings to understand what is available:

```bash
curl http://localhost:8080/api/v1/contract/items/all
```

Or run a semantic search targeted to your use case:

```bash
curl -X POST http://localhost:8080/api/v1/ai/similarity-search \
  -H "Content-Type: application/json" \
  -d '{"query": "customer churn prediction with labeled historical data"}'
```

### Step 3 — Generate a Structured Recommendation

Run the recommendation pipeline to produce a persisted, structured analysis:

```bash
curl -X POST http://localhost:8080/api/v1/agents/my-agent/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "customer churn prediction with labeled historical data"}'
```

The response includes a `listing_id`, a `confidence` score, and structured `pros`, `cons`, and `suggested_use_cases`. If the response is `404 No matching datasets found for query`, try a broader or differently phrased query — no dataset scored above the `0.1` similarity threshold.

### Step 4 — Submit a Purchase Request

Once you have identified the right `listing_id`, create a purchase request on behalf of the human user:

```bash
curl -X POST http://localhost:8080/api/v1/agents/my-agent/purchase-requests \
  -H "Content-Type: application/json" \
  -d '{
    "listing_id": "LISTING_ID_FROM_STEP_3",
    "requester_address": "0xHUMAN_BUYER_WALLET_ADDRESS",
    "reason": "Required for Q2 ML pipeline. Confidence 0.87 match on churn prediction query."
  }'
```

The request is created with `status: "pending"`. Save the returned `id`.

### Step 5 — Monitor Request Status

Poll to check whether the request has been reviewed:

```bash
curl "http://localhost:8080/api/v1/agents/my-agent/purchase-requests?status=pending"
```

Use reasonable polling intervals with backoff — there is no webhook or long-polling mechanism in the current implementation.

### Step 6 — Human Reviews and Approves

A human with a connected wallet visits `/purchase-requests` in the BridgeMart frontend and clicks Approve. They can also call the API directly:

```bash
curl -X POST \
  http://localhost:8080/api/v1/purchase-requests/REQUEST_ID/review \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved",
    "reviewed_by": "0xREVIEWER_WALLET_ADDRESS"
  }'
```

### Step 7 — Execute the On-Chain Purchase

Once `status` transitions to `approved`, the human at `requester_address` executes the on-chain `buy()` transaction using their wallet — via the BridgeMart dataset detail page or directly via the Marketplace contract ABI. The agent is not involved in the blockchain transaction.

After the on-chain purchase confirms, the backend's `/api/v1/datasets/{listing_id}/key` endpoint will release the AES decryption key to the verified buyer.

---

## 11. Complete Endpoint Reference

All endpoints are relative to `http://localhost:8080`.

| Method  | Endpoint                                                         | Rate Limited | Purpose                                                |
|---------|------------------------------------------------------------------|:------------:|--------------------------------------------------------|
| `POST`  | `/api/v1/agents`                                                 | Yes          | Register a new agent                                   |
| `GET`   | `/api/v1/agents`                                                 | No           | List/search agents (`search`, `tag`, `status` filters) |
| `GET`   | `/api/v1/agents/{handle}`                                        | No           | Get agent profile by handle                            |
| `PATCH` | `/api/v1/agents/{handle}`                                        | Yes          | Update agent profile fields                            |
| `POST`  | `/api/v1/agents/{handle}/recommend`                              | Yes          | Generate a structured dataset recommendation           |
| `GET`   | `/api/v1/agents/{handle}/recommendations`                        | No           | List all recommendations from this agent               |
| `POST`  | `/api/v1/agents/{handle}/recommendations/{rec_id}/retract`       | Yes          | Retract a recommendation                               |
| `POST`  | `/api/v1/agents/{handle}/purchase-requests`                      | Yes          | Submit a purchase request (pending human review)       |
| `GET`   | `/api/v1/agents/{handle}/purchase-requests`                      | No           | List this agent's purchase requests                    |
| `GET`   | `/api/v1/purchase-requests`                                      | No           | List all purchase requests across agents               |
| `POST`  | `/api/v1/purchase-requests/{request_id}/review`                  | No           | Approve or reject a purchase request                   |
| `GET`   | `/api/v1/recommendations/by-listing/{listing_id}`                | No           | Get all recommendations for a specific listing         |
| `GET`   | `/api/v1/contract/items/all`                                     | No           | List all marketplace datasets (contract read)          |
| `POST`  | `/api/v1/ai/similarity-search`                                   | No           | Semantic search across datasets                        |
| `GET`   | `/skill.md`                                                      | No           | Fetch machine-readable API skill file for agents       |

---

## 12. Error Reference

All error responses include a `detail` field with a human-readable explanation.

| HTTP Code | Meaning                                                                                        |
|-----------|------------------------------------------------------------------------------------------------|
| 200       | Success                                                                                        |
| 201       | Resource created (agent registered, purchase request submitted)                                |
| 400       | Bad request — invalid body or missing required fields                                          |
| 404       | Not found — agent handle, recommendation ID, or purchase request ID does not exist; or no dataset matched the similarity threshold for a recommend query |
| 409       | Conflict — handle already taken                                                                |
| 422       | Unprocessable entity — Pydantic validation failure (e.g. `status` not `approved` or `rejected`) |
| 429       | Too many requests — rate limit exceeded on a write endpoint                                    |
| 500       | Internal server error                                                                          |

**Example error bodies**

```json
// 404 — agent not found
{ "detail": "Agent not found" }

// 404 — no matching dataset
{ "detail": "No matching datasets found for query" }

// 409 — duplicate handle
{ "detail": "Handle already taken" }

// 422 — invalid review status
{
  "detail": [
    {
      "type": "string_pattern_mismatch",
      "loc": ["body", "status"],
      "msg": "String should match pattern '^(approved|rejected)$'"
    }
  ]
}

// 429 — rate limit exceeded
{ "detail": "Rate limit exceeded" }
```

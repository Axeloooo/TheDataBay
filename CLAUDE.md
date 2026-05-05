# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What Is TheDataBay?

TheDataBay is a **decentralized dataset marketplace** where data sellers publish CSV datasets and buyers purchase access to them using stablecoins (USDC or CADC) on an EVM blockchain. The platform combines on-chain ownership with off-chain storage and AI-powered discovery.

**Core Flow:**
1. **Seller** uploads a CSV → backend encrypts it (AES) → uploads to IPFS via Pinata → calls `Marketplace.createItem()` on-chain with the IPFS hash and price.
2. **Buyer** calls `Marketplace.buyItem()` on-chain with ERC-20 token payment → backend detects the purchase event → releases the AES decryption key.
3. **AI Agents** (on-chain agent profiles) browse listings, generate semantic recommendations, and can submit purchase requests on behalf of users.

**Monorepo Structure:**
```
client/   — React + Vite web frontend
mobile/   — Expo React Native mobile app
api/      — FastAPI Python backend
evm/      — Solidity smart contracts (Foundry)
infra/    — Kubernetes manifests, Terraform, Docker
docs/     — Architecture & runbook documentation
```

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Clients                               │
│   React SPA (client/)          Expo App (mobile/)           │
│   WalletConnect / MetaMask      WalletConnect                │
└────────────┬───────────────────────────┬─────────────────────┘
             │ HTTP/REST                 │ HTTP/REST
             ▼                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (api/)                    │
│                                                             │
│  agents/  ai/  contracts/  datasets/  health/  llm/         │
│  seeds/  shared/  vectorstore/                               │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │  PostgreSQL  │  │   PGVector   │  │ OpenAI / Ollama LLM│ │
│  │  (SQLModel)  │  │ (embeddings) │  │ (embeddings, chat) │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
│                                                             │
│  ┌──────────────┐  ┌──────────────────────────────────────┐ │
│  │  Pinata IPFS │  │  Web3.py → Marketplace.sol (EVM)     │ │
│  │  (datasets)  │  │  Base Sepolia / Anvil (local)         │ │
│  └──────────────┘  └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│               EVM Blockchain (evm/)                         │
│  Marketplace.sol  MockUSDC.sol  MockCADC.sol                │
│  Payment tokens: USDC (6 dec) + CADC (18 dec)               │
└─────────────────────────────────────────────────────────────┘
```

**Infrastructure (Production):** Azure AKS (Kubernetes) + ACR + Key Vault, provisioned by Terraform in `infra/terraform/`.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite + TypeScript + TailwindCSS + shadcn/ui |
| Mobile | Expo (React Native) + TypeScript |
| State | Zustand (persisted to localStorage / AsyncStorage) |
| Wallet | WalletConnect + Reown AppKit + Ethers.js v6 |
| Backend | FastAPI + Uvicorn + Python 3.11 |
| ORM | SQLModel + SQLAlchemy (async) |
| Database | PostgreSQL 15 + pgvector extension |
| LLM | OpenAI (`gpt-4o-mini` / `text-embedding-3-small`) or Ollama |
| Vector DB | PGVector via LangChain |
| IPFS | Pinata (upload) + Pinata Gateway (download) |
| Blockchain | EVM — Base Sepolia (testnet) / Anvil (local) |
| Smart Contracts | Solidity + Foundry + OpenZeppelin |
| IaC | Terraform (Azure: AKS, ACR, Key Vault) |
| Container | Docker + Kubernetes (Azure AKS) |
| CI | GitHub Actions (`.github/workflows/`) |

---

## Key Workflows

### Seller: Upload & List a Dataset

1. Seller connects wallet (WalletConnect).
2. Uploads CSV in the client/mobile upload flow.
3. Backend receives file → generates dataset preview + stats → generates row embeddings via LLM → stores vectors in PGVector.
4. Backend encrypts the CSV with AES → uploads ciphertext to Pinata IPFS → stores `DatasetKey` in Postgres.
5. Client calls `Marketplace.createItem(id, name, description, tokenAddress, price, ipfsUrl, hash, signature, sigHash)` on-chain.
6. Listing is now live; metadata is frozen after first purchase.

### Buyer: Discover & Purchase

1. Buyer enters a semantic search query.
2. Backend embeds the query → runs cosine similarity search in PGVector → ranks results → returns top-K listings.
3. Buyer selects a dataset, approves the ERC-20 token spend, calls `Marketplace.buyItem(id)` on-chain.
4. Backend detects purchase (via `hasAccess` check) → returns AES decryption key from `DatasetKey` table.
5. Client decrypts and downloads the dataset.

### AI Agent: Recommend & Purchase

1. Agent profiles exist on-chain (managed via `/api/v1/agents`).
2. Agent runs similarity search → creates `AgentRecommendation` (stored in Postgres).
3. Agent submits `AgentPurchaseRequest`; human reviews and approves/rejects it.
4. Approved request triggers on-chain `buyItem` via server-signed transaction.

---

## Commands

### Client (`client/`)

```bash
npm run dev        # Start dev server → http://localhost:5173
npm run build      # TypeScript check + production build
npm run lint       # ESLint
npm run preview    # Preview production build
```

### Mobile (`mobile/`)

```bash
npm run start      # Start Expo dev server
npm run ios        # iOS simulator
npm run android    # Android emulator
npm run web        # Expo web target
npm run lint       # ESLint
npm run test       # Jest tests (--runInBand)
```

### API (`api/`)

```bash
cd api && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

pytest                                             # All tests (≥55% coverage required)
pytest tests/unit/llm/ -q                          # LLM unit tests
pytest -k "test_name" -q                           # Single test
```

### Smart Contracts (`evm/`)

```bash
make anvil                     # Start local Anvil node (port 8545, chain ID 31337)
make deploy-anvil              # Deploy Marketplace → syncs addresses to .env
make seed-anvil                # Seed demo listings
make mint-tokens-anvil         # Mint MockUSDC + MockCADC on Anvil
make mint-tokens-base-sepolia  # Mint tokens on Base Sepolia
make evm-build                 # Compile + export ABI to api/app/contracts/
make evm-test                  # Run Foundry tests
make evm-fmt                   # Format Solidity
```

### Dev Environment (Minikube)

```bash
make dev-up    # Start full stack with Tilt + Minikube
make dev-down  # Stop Tilt session
```

### Terraform (Production)

```bash
make tf-init    # terraform init (production)
make tf-plan    # terraform plan
make tf-apply   # terraform apply
```

### Kubernetes

```bash
make k8s-deploy-prod  # Apply all production manifests (ordered)
make k8s-status       # Show pod + ingress status
make k8s-rollback     # Roll back backend + frontend deployments
```

---

## API Architecture (Domain-Driven / Screaming Architecture)

```
api/app/
├── agents/           # Agent profiles, recommendations, purchase requests
│   ├── models.py     # SQLModel: Agent, AgentRecommendation, AgentPurchaseRequest
│   ├── router.py     # /api/v1/agents  /api/v1/recommendations  /api/v1/purchase-requests
│   ├── service.py
│   └── schemas.py
├── ai/               # Semantic similarity search
│   ├── router.py     # /api/v1/ai
│   ├── service.py    # Embeds query → PGVector cosine search → ranked results
│   └── schemas.py
├── config/
│   └── settings.py   # Pydantic BaseSettings; all config from env vars
├── contracts/        # On-chain marketplace integration (Web3.py)
│   ├── router.py     # /api/v1/contract
│   ├── service.py    # createItem, buyItem, hasAccess, getItems, …
│   └── schemas.py
├── database/
│   └── engine.py     # SQLAlchemy async engine; session factory
├── datasets/         # CSV upload, encryption, IPFS, key storage, preview
│   ├── models.py     # SQLModel: DatasetKey, DatasetPreview
│   ├── router.py     # /api/v1/datasets
│   ├── service.py    # encrypt → IPFS → preview → embed pipeline
│   └── schemas.py
├── health/
│   └── router.py     # GET /health  GET /health/ready
├── llm/              # Multi-provider LLM abstraction
│   ├── providers/
│   │   ├── __init__.py   # Registry factory (LLM_PROVIDER env var)
│   │   ├── ollama.py     # OllamaLLMService (expand_column_names, embed_text/s)
│   │   └── openai.py     # OpenAILLMService
│   ├── service.py    # LLMService abstract base
│   ├── schemas.py    # EmbeddingResult, ColumnExpansionResult, …
│   └── errors.py     # LLMProviderError, LLMResponseValidationError, …
├── seeds/            # Demo data (agents, mock marketplace items)
├── shared/           # Cross-cutting utilities
│   ├── encryption.py # AES encrypt/decrypt
│   ├── ipfs.py       # Pinata upload_bytes()
│   ├── errors.py     # HTTP exception helpers
│   └── rate_limiter.py # In-process sliding-window rate limiter
├── vectorstore/
│   └── repositories/
│       └── pgvector_repository.py  # add_documents(), similarity_search_by_vector()
└── main.py           # FastAPI app init, router registration, startup events
```

### Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health/` | Liveness check |
| `GET` | `/health/ready` | Readiness check |
| `POST` | `/api/v1/datasets/embed` | Upload + encrypt + embed dataset |
| `GET` | `/api/v1/datasets/{id}/preview` | Dataset preview + stats |
| `POST` | `/api/v1/datasets/{id}/key` | Release decryption key (purchase-gated) |
| `POST` | `/api/v1/ai/embed/query` | Semantic similarity search |
| `GET` | `/api/v1/contract/items/all` | All on-chain listings |
| `GET` | `/api/v1/contract/items/{id}` | Single listing |
| `POST` | `/api/v1/contract/buy` | Purchase item (server-signed) |
| `GET` | `/api/v1/agents/` | List agents |
| `POST` | `/api/v1/agents/` | Create agent |
| `GET` | `/api/v1/agents/{handle}` | Agent profile |
| `POST` | `/api/v1/recommendations/` | Create recommendation |
| `GET` | `/api/v1/recommendations/{id}` | Get recommendation |
| `POST` | `/api/v1/purchase-requests/` | Submit purchase request |
| `POST` | `/api/v1/purchase-requests/{id}/review` | Approve / reject request |

---

## Database Schema

**PostgreSQL** — connection via `POSTGRES_URL`. Tables created automatically on startup.

| Table | Model | Key Fields |
|-------|-------|-----------|
| `agent` | `Agent` | `id` UUID, `handle` (unique), `display_name`, `owner_address`, `capability_tags` JSON, `verification_status`, `is_active` |
| `agentrecommendation` | `AgentRecommendation` | `id` UUID, `agent_id` FK, `listing_id`, `confidence`, `similarity_score`, `rationale`, `pros`/`cons`/`suggested_use_cases` JSON |
| `agentpurchaserequest` | `AgentPurchaseRequest` | `id` UUID, `agent_id` FK, `listing_id`, `requester_address`, `status` (pending/approved/rejected), `reviewed_at` |
| `dataset_keys` | `DatasetKey` | `id` UUID, `listing_id` (unique), `key_b64`, `nonce_b64`, `dataset_url`, `dataset_hash` |
| `dataset_previews` | `DatasetPreview` | `id` UUID, `listing_id` (unique), `preview` JSON, `stats` JSON, `vector_spec` JSON |

**PGVector** — embeddings stored as vectors in a separate LangChain-managed collection (`dataset_rows`). Queried via cosine similarity in `ai/service.py`.

---

## Smart Contracts (`evm/`)

**`Marketplace.sol`** — single contract handling all marketplace logic.

```
Security: Ownable + ReentrancyGuard + SafeERC20
Payment tokens: USDC (6 decimals) + CADC (18 decimals)
Fee model: basis points (bps), configurable recipient
Metadata frozen after first purchase (immutable integrity guarantee)
```

| Function | Description |
|----------|-------------|
| `createItem(...)` | List a dataset (IPFS URL, price, token, signature) |
| `buyItem(bytes32)` | Purchase — transfers ERC-20, emits `ItemPurchased` |
| `hasAccess(bytes32, bytes32)` | Check wallet access rights |
| `grantAccess(bytes32, bytes32)` | Grant access (owner only) |
| `getItemView(bytes32)` | Single listing view |
| `getAllItems()` | All listings |
| `getItems(offset, limit)` | Paginated listings |
| `updatePrice(bytes32, uint256)` | Update price (pre-sale only) |
| `setFeeConfig(address, uint256)` | Set fee recipient + bps |
| `addAcceptedToken(address, uint8, uint256)` | Add payment token |

After `make evm-build`, the ABI is exported to `api/app/contracts/Marketplace.json`.

---

## Client & Mobile

### Client (`client/src/`)

**Pages** (`pages/`): `Home`, `Upload`, `DatasetDetail`, `Agents`, `AgentProfile`, `PurchaseRequests`, `HowItWorks`, `Layout`, `NotFound`

**Stores** (`stores/`, Zustand): `upload-store`, `agent-store`, `wallet-store`, `currency-store`, `search-store`, `theme-store`

- Path alias: `@/*` → `src/*`
- Wallet: WalletConnect via `window.ethereum` + Ethers.js v6
- Vite `define` block remaps `API_URL`/`CONTRACT_ADDRESS`/etc. → `VITE_*` vars; falls back to `VITE_*` prefixed vars for Docker builds

### Mobile (`mobile/src/`)

**Routes** (`app/`): Tabbed layout — `(tabs)/index` (Home), `(tabs)/search`, `(tabs)/upload`, `(tabs)/wallet`, `dataset/[id]`

**Stores** (`stores/`): `upload-store`, `marketplace-store`, `wallet-store`, `currency-store`, `search-store`

- Expo Router for file-based routing
- Reown AppKit + WalletConnect for EVM wallet sessions
- Shared business logic with the web client

---

## Environment Setup

Copy `.env.example` → `.env` at the monorepo root. All services read from it.

```bash
# Quick start (local dev)
cp .env.example .env
# Fill in: OPENAI_API_KEY, PINATA_API_KEY, PINATA_SECRET_KEY, WALLETCONNECT_PROJECT_ID
# After make deploy-anvil: CONTRACT_ADDRESS, USDC_TOKEN_ADDRESS, CADC_TOKEN_ADDRESS are auto-synced
```

Key variable groups:

| Group | Variables |
|-------|-----------|
| **LLM** | `LLM_PROVIDER` (`openai`/`ollama`), `LLM_CHAT_MODEL`, `LLM_EMBEDDING_MODEL`, `LLM_EMBEDDING_DIMENSION`, `OPENAI_API_KEY`, `OLLAMA_API_KEY`, `LLM_BASE_URL` |
| **Database** | `POSTGRES_URL`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` |
| **IPFS** | `PINATA_API_KEY`, `PINATA_SECRET_KEY`, `PINATA_GATEWAY_URL` |
| **Blockchain** | `RPC_URL`, `CHAIN_ID`, `CONTRACT_ADDRESS`, `USDC_TOKEN_ADDRESS`, `CADC_TOKEN_ADDRESS`, `SERVER_PRIVATE_KEY`, `CONTRACT_ABI_PATH` |
| **Client** | `API_URL`, `WALLETCONNECT_PROJECT_ID` |
| **Search** | `TOP_K`, `SIMILARITY_THRESHOLD`, `CACHE_MAXSIZE` |
| **Upload** | `MAX_FILE_SIZE_MB`, `MAX_DATASET_ROWS` |

---

## Deployment

### Production Architecture (Azure)

```
GitHub Actions
     │ push to main
     ▼
Azure Container Registry (ACR)
     │ docker push api:sha  ui:sha
     ▼
Azure AKS (Kubernetes)                Azure Key Vault
  thedatabay namespace                    ↕ secrets-store-csi
  ├── backend-deployment   ←─────────────── thedatabay-secrets
  ├── frontend-deployment
  ├── postgres-statefulset
  ├── ingress (nginx + cert-manager → thedatabay.com)
  └── hpa / pdb
```

### First-Time Infrastructure Provisioning

```bash
# 1. Bootstrap Terraform remote state (Azure Storage)
az group create -n thedatabay-tfstate-rg -l mexicocentral
az storage account create -n thedatabaystate -g thedatabay-tfstate-rg --sku Standard_LRS
az storage container create -n tfstate --account-name thedatabaystate

# 2. Provision Azure resources
make tf-init && make tf-plan && make tf-apply

# 3. Populate Key Vault secrets (from .env or CI secrets)
# See infra/DEPLOYMENT.md for az keyvault secret set commands

# 4. Deploy to Kubernetes
az aks get-credentials --resource-group thedatabay-production-rg --name thedatabay-production-aks
make k8s-deploy-prod
```

### Rolling Update (after Terraform apply)

```bash
# Build + push images
ACR_NAME=$(terraform -chdir=infra/terraform/environments/production output -raw acr_login_server)
TAG=$(git rev-parse --short HEAD)
az acr login --name "${ACR_NAME%%.azurecr.io}"
docker build -f infra/docker/production/api.Dockerfile -t "$ACR_NAME/thedatabay/api:$TAG" .
docker build -f infra/docker/production/client.Dockerfile -t "$ACR_NAME/thedatabay/ui:$TAG" .
docker push "$ACR_NAME/thedatabay/api:$TAG"
docker push "$ACR_NAME/thedatabay/ui:$TAG"

# Update deployments
kubectl set image deployment/backend backend="$ACR_NAME/thedatabay/api:$TAG" -n thedatabay
kubectl set image deployment/frontend frontend="$ACR_NAME/thedatabay/ui:$TAG" -n thedatabay
```

### Kubernetes Manifests (apply order matters)

```
infra/k8s/production/
├── namespace.yaml                     # 1. Namespace
├── cert-manager/cluster-issuer.yaml   # 2. TLS issuer
├── secret-provider-class.yaml         # 3. Key Vault CSI
├── postgres-statefulset.yaml          # 4. Database
├── backend-deployment.yaml            # 5. API
├── frontend-deployment.yaml           # 6. UI
├── ingress.yaml                       # 7. Routing + TLS
├── hpa.yaml                           # 8. Autoscaler
└── pdb.yaml                           # 9. Disruption budget
```

---

## Agent Skills

Skills are located under `.agents/skills/` (shared across agents in this repo).
Agents **must read the selected skill's `SKILL.md` before implementation** and follow its workflow, constraints, and quality checks.

### Skill Loading Protocol (Required)

1. **Classify the request** by domain (`client/`, `mobile/`, `api/`, `evm/`, docs/copy, debugging, or orchestration).
2. **Load mandatory foundation skills first**:
   - `brainstorming` before creative feature work, behavior changes, or significant refactors.
   - `systematic-debugging` before attempting fixes for bugs, flaky tests, or unknown failures.
3. **Load one or more domain skills** based on touched code.
4. **Compose skills when needed** (foundation + domain + specialist), avoiding conflicting instructions.
5. **Execute and verify** using commands/tests defined in this document.
6. **Report what was used** in the final response (which skills drove decisions and checks).

### Skill Selection Matrix

| Skill | Path | Primary trigger |
|-------|------|----------------|
| `api-design-principles` | `.agents/skills/api-design-principles/` | API contract design, endpoint semantics |
| `brainstorming` | `.agents/skills/brainstorming/` | Any new feature, behavior change, or significant refactor |
| `copywriting` | `.agents/skills/copywriting/` | Marketing/product copy improvements |
| `e2e-testing-patterns` | `.agents/skills/e2e-testing-patterns/` | End-to-end testing, Playwright/Cypress |
| `fastapi-templates` | `.agents/skills/fastapi-templates/` | FastAPI route/service scaffolding |
| `frontend-design` | `.agents/skills/frontend-design/` | UI-heavy pages/components |
| `github-actions-templates` | `.agents/skills/github-actions-templates/` | CI/CD workflow setup |
| `postgresql-table-design` | `.agents/skills/postgresql-table-design/` | PostgreSQL schema, pgvector |
| `python-testing-patterns` | `.agents/skills/python-testing-patterns/` | pytest fixtures, mocking |
| `react-state-management` | `.agents/skills/react-state-management/` | Zustand refactors in `client/` or `mobile/` |
| `requesting-code-review` | `.agents/skills/requesting-code-review/` | Final verification before merge |
| `shadcn` | `.agents/skills/shadcn/` | shadcn/ui components in `client/` |
| `skill-creator` | `.agents/skills/skill-creator/` | Create or update skills |
| `solskill` | `.agents/skills/solskill/` | Solidity/Foundry contract logic |
| `subagent-driven-development` | `.agents/skills/subagent-driven-development/` | Parallelizable multi-track work |
| `systematic-debugging` | `.agents/skills/systematic-debugging/` | Bug investigation, failing tests |
| `terraform-style-guide` | `.agents/skills/terraform-style-guide/` | Terraform authoring/review |
| `terraform-test` | `.agents/skills/terraform-test/` | Terraform `.tftest.hcl` files |
| `test-driven-development` | `.agents/skills/test-driven-development/` | Tests-first implementation |
| `typescript-advanced-types` | `.agents/skills/typescript-advanced-types/` | Complex TS generics, utility types |
| `vercel-react-best-practices` | `.agents/skills/vercel-react-best-practices/` | `client/` React/Vite changes |
| `vercel-react-native-skills` | `.agents/skills/vercel-react-native-skills/` | `mobile/` Expo/React Native |
| `writing-plans` | `.agents/skills/writing-plans/` | Multi-step implementation plans |

### Recommended Skill Combinations

- **New API endpoint**: `brainstorming` → `api-design-principles` + `fastapi-templates`
- **API bug/regression**: `systematic-debugging` → `api-design-principles` (+ `fastapi-templates` if structural)
- **Client UI feature**: `brainstorming` → `frontend-design` + `vercel-react-best-practices` (+ `shadcn`)
- **State management changes**: `brainstorming` → `react-state-management` (+ `typescript-advanced-types`)
- **Mobile feature**: `brainstorming` or `systematic-debugging` → `vercel-react-native-skills`
- **Contract feature/fix**: `brainstorming` or `systematic-debugging` → `solskill`
- **New backend service + tests**: `brainstorming` → `fastapi-templates` + `api-design-principles` + `test-driven-development` + `python-testing-patterns`
- **DB schema change**: always load `postgresql-table-design`
- **Python test work**: `python-testing-patterns` + `fastapi-templates` (+ `systematic-debugging` for regressions)
- **CI/CD automation**: `github-actions-templates`
- **Terraform delivery**: `terraform-style-guide` + `terraform-test`
- **Large scoped effort**: `writing-plans` → `subagent-driven-development`
- **Pre-merge validation**: `requesting-code-review`

## Specs & Planning

Feature specs live in the Obsidian Vault at `/Users/axelsanchez/Code/Obsidian Vault/`.
When a task references a spec, read the relevant vault note before loading any skills.

| Feature | Vault Note |
|---------|-----------|
| Semantic Search refactor | `/Users/axelsanchez/Code/Obsidian Vault/Semantic Search.md` |
| CADC payment integration | `/Users/axelsanchez/Code/Obsidian Vault/CADC.md` |
| Backend architecture refactor | `/Users/axelsanchez/Code/Obsidian Vault/Backend Architecture.md` |
| Dataset preview | `/Users/axelsanchez/Code/Obsidian Vault/Dataset Preview.md` |

### Anti-Patterns (Do Not Do)

- Starting implementation without reading the relevant `SKILL.md`.
- Using only domain skills when debugging is required.
- Applying `frontend-design` for purely data/model/backend tasks.
- Overusing `subagent-driven-development` for tightly coupled, sequential edits.
- Skipping test-focused skills when verification scope changes.
- Reaching for `github-actions-templates` or `terraform-style-guide` outside CI/IaC work.

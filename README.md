# BridgeMart

![Status](https://img.shields.io/badge/status-beta-orange)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)
![Node](https://img.shields.io/badge/node-20.x-339933)
![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)
![Foundry](https://img.shields.io/badge/foundry-forge%2Fanvil-black)
![Kubernetes](https://img.shields.io/badge/k8s-minikube-326CE5)

Decentralized dataset marketplace with encrypted dataset delivery, on-chain listing/payment, and semantic discovery.

## 📚 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Command Catalog](#-command-catalog)
- [API Endpoints](#-api-endpoints)
- [Seed On-Chain Test Data](#-seed-on-chain-test-data)
- [Troubleshooting](#-troubleshooting)

## 🔭 Overview

BridgeMart includes:
- `client/`: React + Vite frontend
- `server/`: FastAPI backend (LLM jobs, key release, contract reads)
- `evm/`: Foundry smart contracts/scripts/tests
- `infra/development/`: Kubernetes manifests and Dockerfiles used in local dev

## 🧱 Architecture

- Listings are stored and read from `Marketplace` contract.
- Dataset payloads are encrypted before IPFS upload.
- Signature files remain unencrypted.
- Buyers obtain decryption keys via backend key release endpoint, gated by on-chain `hasAccess`.
- Similarity search runs via `/api/v1/ai/similarity-search` and ranks on marketplace signature vectors.

## ✅ Prerequisites

- Node.js `20.x` (recommended for Vite/esbuild stability)
- Python `3.11+`
- Foundry (`forge`, `cast`, `anvil`)
- Docker
- Minikube + kubectl
- Tilt

## 🚀 Quick Start

### 1) Start local chain and deploy contract

```bash
cd evm
make anvil
# in another terminal
make deploy-anvil
make seed-anvil
```

### 2) Run backend

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3) Run frontend

```bash
cd client
npm install
npm run dev
```

Set frontend env values:

```bash
VITE_API_URL=http://localhost:8000
VITE_CONTRACT_ADDRESS=<deployed_marketplace_address>
VITE_PINATA_GATEWAY_URL=https://gateway.pinata.cloud
```

## 🛠️ Command Catalog

### 🖥️ Frontend (`client/`)

| Command | What it does |
|---|---|
| `npm run dev` | Start Vite dev server |
| `npm run build` | Type-check and production build |
| `npm run lint` | Run ESLint |
| `npm run preview` | Serve built app locally |

### ⚙️ Backend (`server/`)

| Command | What it does |
|---|---|
| `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` | Run API locally with reload |
| `pytest` | Run all tests |
| `pytest tests/services -q` | Run service-level tests only |
| `pytest tests/services/test_contract_service.py -q` | Focus contract service tests |

### ⛓️ EVM / Foundry (`evm/`)

| Command | What it does |
|---|---|
| `forge build` | Compile contracts |
| `forge test` | Run solidity test suite |
| `make anvil` | Start local anvil node |
| `make deploy-anvil` | Deploy `Marketplace` to local anvil |
| `make seed-anvil` | Seed deterministic demo listings on-chain |
| `make getall` | Read all on-chain items with `cast` |
| `make buy-item ITEM_ID=<bytes32> PRICE_WEI=<wei>` | Buy seeded item from CLI |

### 🐳 Docker

| Command | What it does |
|---|---|
| `docker build -f infra/development/docker/client.Dockerfile -t bridgemart/client .` | Build frontend image |
| `docker build -f infra/development/docker/server.Dockerfile -t bridgemart/server .` | Build backend image |
| `docker images \| grep bridgemart` | Verify built images |

### ☸️ Minikube / Kubernetes / Tilt

| Command | What it does |
|---|---|
| `minikube start` | Start local Kubernetes cluster |
| `minikube status` | Check cluster health |
| `tilt up` | Build and deploy local development stack |
| `tilt down` | Stop Tilt session |
| `kubectl get pods -A` | Inspect all pods |
| `kubectl get svc -A` | Inspect services |
| `kubectl logs deployment/server -n default` | View server logs |
| `kubectl logs deployment/client -n default` | View client logs |
| `kubectl logs statefulset/postgres -n default` | View postgres logs |
| `kubectl port-forward svc/server-svc 8080:8080` | Expose backend locally |
| `kubectl port-forward svc/client-svc 5173:5173` | Expose frontend locally |

## 🔌 API Endpoints

### Health

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health/` | Basic service health |
| `GET` | `/health/ready` | Readiness/dependency status |

### LLM / Jobs

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/llm/embed/batch` | Upload CSV, enqueue embedding/encryption job |
| `GET` | `/api/v1/llm/jobs/{job_id}` | Poll job status |
| `POST` | `/api/v1/llm/embed/query` | Query embedding generation |

### Similarity Search

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/ai/similarity-search` | Semantic ranking of marketplace datasets |

### Datasets / Key Release

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/datasets/{listing_id}/key` | Release AES key/nonce if wallet has on-chain access |

### Contract Read/Utility

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/contract/items/all` | Get all listings |
| `GET` | `/api/v1/contract/items/{listing_id}` | Get single listing |
| `POST` | `/api/v1/contract/access/{listing_id}/check` | Check wallet access |
| `GET` | `/api/v1/contract/fee-bps` | Current marketplace fee |
| `GET` | `/api/v1/contract/owner` | Contract owner |

### Contract Write/Admin (server-signed where enabled)

| Method | Endpoint | Purpose |
|---|---|---|
| `PATCH` | `/api/v1/contract/items/{listing_id}/dataset-url` | Update dataset URL |
| `PATCH` | `/api/v1/contract/items/{listing_id}/signature` | Update signature URL/hash |
| `PATCH` | `/api/v1/contract/items/{listing_id}/price` | Update listing price |
| `PATCH` | `/api/v1/contract/fee-config` | Update fee recipient/bps |
| `POST` | `/api/v1/contract/items/{listing_id}/grant-access` | Grant access for walletId |

## 🌱 Seed On-Chain Test Data

Use this flow to populate Home/Detail pages with real on-chain listings.

```bash
cd evm
make anvil
# new terminal
make deploy-anvil
make seed-anvil
make getall
```

`make seed-anvil` uses `evm/script/SeedMarketplace.s.sol` and creates deterministic UUID-compatible `bytes32` item IDs so frontend route + backend UUID conversion remain consistent.

## 🧰 Troubleshooting

### MetaMask connected but create/buy fails

- Verify MetaMask network is your anvil chain (`31337` by default).
- Verify selected account matches expected seller flow for `createItem`.
- Verify `VITE_CONTRACT_ADDRESS` points to deployed contract on the same chain.

### Error: no contract code found at configured address

- Address is wrong for the active chain or deployment changed.
- Re-run `make deploy-anvil` and update `VITE_CONTRACT_ADDRESS`.

### `Marketplace__ItemDoesNotExist(bytes32)`

- Listing is being queried before on-chain creation.
- Confirm create transaction is mined, then refresh item view.
- Use `make getall` to verify listing presence.

### Similarity search returns no results

- Signature files may be missing/unavailable or below threshold.
- Validate `signature_url`/`signature_hash` for listed items.
- Try broader query terms.

# Ulenor

[![CI](https://github.com/Axeloooo/Ulenor/actions/workflows/test.yml/badge.svg)](https://github.com/Axeloooo/Ulenor/actions/workflows/test.yml)
[![Release](https://github.com/Axeloooo/Ulenor/actions/workflows/release.yml/badge.svg)](https://github.com/Axeloooo/Ulenor/actions/workflows/release.yml)
[![Tag](https://img.shields.io/github/v/tag/Axeloooo/Ulenor?label=tag)](https://github.com/Axeloooo/Ulenor/tags)
[![License](https://img.shields.io/github/license/Axeloooo/Ulenor)](https://github.com/Axeloooo/Ulenor/blob/main/LICENSE)
[![Issues](https://img.shields.io/github/issues/Axeloooo/Ulenor)](https://github.com/Axeloooo/Ulenor/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/Axeloooo/Ulenor)](https://github.com/Axeloooo/Ulenor/pulls)
[![Contributors](https://img.shields.io/github/contributors/Axeloooo/Ulenor)](https://github.com/Axeloooo/Ulenor/graphs/contributors)
[![Repo Size](https://img.shields.io/github/repo-size/Axeloooo/Ulenor)](https://github.com/Axeloooo/Ulenor)

Decentralized dataset marketplace with encrypted dataset delivery, on-chain listing/payment, and semantic discovery.

## 📚 Table of Contents

- [Overview](#-overview)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Command Catalog](#-command-catalog)
- [API Endpoints](#-api-endpoints)
- [Seed On-Chain Test Data](#-seed-on-chain-test-data)
- [Troubleshooting](#-troubleshooting)

## 🔭 Overview

Ulenor includes:

- `client/`: React + Vite frontend
- `mobile/`: Expo React Native app (wallet, search, upload, purchases)
- `api/`: FastAPI backend (LLM jobs, key release, contract reads)
- `evm/`: Foundry smart contracts/scripts/tests
- `infra/development/`: Kubernetes manifests and Dockerfiles used in local dev

## 🧩 Tech Stack

| Layer           | Stack                                                             | Paths                            |
| --------------- | ----------------------------------------------------------------- | -------------------------------- |
| Web app         | React, TypeScript, Vite, Zustand, Ethers.js                       | `client/`                        |
| Mobile app      | Expo, React Native, Expo Router, Zustand, Reown AppKit, Ethers.js | `mobile/`                        |
| Backend API     | FastAPI, SQLModel, Pydantic, pytest                               | `api/`                           |
| Smart contracts | Solidity, Foundry (forge/anvil/cast), OpenZeppelin                | `evm/`                           |
| Dev infra       | Docker, Kubernetes (Minikube), Tilt                               | `infra/development/`, `tiltfile` |

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
make anvil
# in another terminal
make deploy-anvil
make seed-anvil
```

`make anvil` listens on `0.0.0.0:8545` by default so Tilt/Kubernetes backend pods can reach the host node. For a purely host-local chain, run `ANVIL_HOST=127.0.0.1 make anvil`.

### 2) Run backend

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### 3) Run frontend

```bash
cd client
npm install
npm run dev
```

Copy `.env.example` → `.env` at the repo root and fill in the values before starting the dev server.

### 4) Run mobile app

```bash
cd mobile
npm install
npm run start
```

## 🛠️ Command Catalog

### 🖥️ Frontend (`client/`)

| Command           | What it does                    |
| ----------------- | ------------------------------- |
| `npm run dev`     | Start Vite dev server           |
| `npm run build`   | Type-check and production build |
| `npm run lint`    | Run ESLint                      |
| `npm run preview` | Serve built app locally         |

### ⚙️ Backend (`api/`)

| Command                    | What it does                               |
| -------------------------- | ------------------------------------------ |
| `fastapi dev`              | Run API locally with reload                |
| `pytest`                   | Run all tests except integration (default) |
| `pytest tests/unit -q`     | Run unit tests only (no Docker required)   |
| `pytest -m integration -q` | Run integration tests (requires Docker)    |
| `pytest -k "test_name" -q` | Run a single test by name                  |

### 📱 Mobile (`mobile/`)

| Command           | What it does           |
| ----------------- | ---------------------- |
| `npm run start`   | Start Expo dev server  |
| `npm run ios`     | Launch iOS target      |
| `npm run android` | Launch Android target  |
| `npm run web`     | Launch web target      |
| `npm run lint`    | Run Expo/ESLint checks |
| `npm run test`    | Run mobile Jest tests  |

### ⛓️ EVM / Foundry (`evm/`)

| Command                          | What it does                                          |
| -------------------------------- | ----------------------------------------------------- |
| `make evm-build`                 | Compile contracts, export ABI to `api/app/contracts/` |
| `make evm-test`                  | Run Solidity test suite                               |
| `make anvil`                     | Start local Anvil node on `0.0.0.0:8545`              |
| `make deploy-anvil`              | Deploy `Marketplace` to local Anvil                   |
| `make seed-anvil`                | Seed deterministic demo listings on-chain             |
| `make mint-tokens-anvil`         | Mint MockUSDC + MockCADC on Anvil                     |
| `make mint-tokens-base-sepolia`  | Mint MockUSDC + MockCADC on Base Sepolia               |

### 🐳 Docker

| Command                                                                             | What it does         |
| ----------------------------------------------------------------------------------- | -------------------- |
| `docker build -f infra/development/docker/client.Dockerfile -t ulenor/client .` | Build frontend image |
| `docker build -f infra/development/docker/server.Dockerfile -t ulenor/server .` | Build backend image  |
| `docker images \| grep ulenor`                                                  | Verify built images  |

### ☸️ Minikube / Kubernetes / Tilt

| Command                                         | What it does                             |
| ----------------------------------------------- | ---------------------------------------- |
| `minikube start`                                | Start local Kubernetes cluster           |
| `minikube status`                               | Check cluster health                     |
| `tilt up`                                       | Build and deploy local development stack |
| `tilt down`                                     | Stop Tilt session                        |
| `kubectl get pods -A`                           | Inspect all pods                         |
| `kubectl get svc -A`                            | Inspect services                         |
| `kubectl logs deployment/api -n default`        | View server logs                         |
| `kubectl logs deployment/client -n default`     | View client logs                         |
| `kubectl logs statefulset/postgres -n default`  | View postgres logs                       |
| `kubectl port-forward svc/api-svc 8080:8080`    | Expose backend locally                   |
| `kubectl port-forward svc/client-svc 5173:5173` | Expose frontend locally                  |

## 🔌 API Endpoints

### Health

| Method | Endpoint        | Purpose                     |
| ------ | --------------- | --------------------------- |
| `GET`  | `/health/`      | Basic service health        |
| `GET`  | `/health/ready` | Readiness/dependency status |

### LLM / Jobs

| Method | Endpoint                    | Purpose                                      |
| ------ | --------------------------- | -------------------------------------------- |
| `POST` | `/api/v1/llm/embed/batch`   | Upload CSV, enqueue embedding/encryption job |
| `GET`  | `/api/v1/llm/jobs/{job_id}` | Poll job status                              |
| `POST` | `/api/v1/llm/embed/query`   | Query embedding generation                   |

### Similarity Search

| Method | Endpoint                       | Purpose                                  |
| ------ | ------------------------------ | ---------------------------------------- |
| `POST` | `/api/v1/ai/similarity-search` | Semantic ranking of marketplace datasets |

### Datasets / Key Release

| Method | Endpoint                            | Purpose                                             |
| ------ | ----------------------------------- | --------------------------------------------------- |
| `POST` | `/api/v1/datasets/{listing_id}/key` | Release AES key/nonce if wallet has on-chain access |

### Contract Read/Utility

| Method | Endpoint                                     | Purpose                 |
| ------ | -------------------------------------------- | ----------------------- |
| `GET`  | `/api/v1/contract/items/all`                 | Get all listings        |
| `GET`  | `/api/v1/contract/items/{listing_id}`        | Get single listing      |
| `POST` | `/api/v1/contract/access/{listing_id}/check` | Check wallet access     |
| `GET`  | `/api/v1/contract/fee-bps`                   | Current marketplace fee |
| `GET`  | `/api/v1/contract/owner`                     | Contract owner          |

### Contract Write/Admin (server-signed where enabled)

| Method  | Endpoint                                           | Purpose                   |
| ------- | -------------------------------------------------- | ------------------------- |
| `PATCH` | `/api/v1/contract/items/{listing_id}/dataset-url`  | Update dataset URL        |
| `PATCH` | `/api/v1/contract/items/{listing_id}/signature`    | Update signature URL/hash |
| `PATCH` | `/api/v1/contract/items/{listing_id}/price`        | Update listing price      |
| `PATCH` | `/api/v1/contract/fee-config`                      | Update fee recipient/bps  |
| `POST`  | `/api/v1/contract/items/{listing_id}/grant-access` | Grant access for walletId |

## 🌱 Seed On-Chain Test Data

Use this flow to populate Home/Detail pages with real on-chain listings.

```bash
make anvil
# new terminal
make deploy-anvil
make seed-anvil
```

`make seed-anvil` uses `evm/script/SeedMarketplace.s.sol` and creates deterministic UUID-compatible `bytes32` item IDs so frontend route + backend UUID conversion remain consistent.

`make deploy-anvil` also syncs the deployed marketplace address into `infra/k8s/development/secrets.yaml` and the root `.env`.

For Tilt/Kubernetes, set `infra/k8s/development/secrets.yaml` `RPC_URL` to a host-reachable URL such as `http://host.docker.internal:8545`. Use `http://127.0.0.1:8545` only when the backend process itself runs directly on the host.

## 🧰 Troubleshooting

### MetaMask connected but create/buy fails

- Verify MetaMask network is your anvil chain (`31337` by default).
- Verify selected account matches expected seller flow for `createItem`.
- Verify `VITE_CONTRACT_ADDRESS` points to deployed contract on the same chain.
- Verify `VITE_PAYMENT_TOKEN_ADDRESS` points to the accepted USDC token for that deployment.

### Error: no contract code found at configured address

- Address is wrong for the active chain or deployment changed.
- Re-run `make deploy-anvil` so local config files are refreshed with the new address.

### `getAllItems()` reverts in the backend but `make getall` works

- Check that the backend is calling the same deployed address saved in `evm/deployments/anvil_marketplace.addr`.
- If you redeployed Anvil, re-run `make deploy-anvil` to sync `infra/k8s/development/secrets.yaml` and the root `.env`.
- Restart the server resource after the config update so the new `CONTRACT_ADDRESS` is loaded.

### Error: RPC node unreachable

- Verify Anvil is running with `make anvil`. The default target binds to `0.0.0.0:8545` so containers can reach it.
- If the backend runs in Tilt/Kubernetes, set `infra/k8s/development/secrets.yaml` `RPC_URL` to `http://host.docker.internal:8545`, then restart the server resource so the secret is reloaded.
- If the backend runs directly on your host with `uvicorn`, `RPC_URL=http://127.0.0.1:8545` is correct.

### `Marketplace__ItemDoesNotExist(bytes32)`

- Listing is being queried before on-chain creation.
- Confirm create transaction is mined, then refresh item view.
- Use `make getall` to verify listing presence.

### Similarity search returns no results

- Signature files may be missing/unavailable or below threshold.
- Validate `signature_url`/`signature_hash` for listed items.
- Try broader query terms.

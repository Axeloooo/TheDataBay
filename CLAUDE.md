# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BridgeMart is a decentralized dataset marketplace monorepo with four main components:
- `client/` — React + Vite web frontend
- `mobile/` — Expo React Native mobile app
- `server/` — FastAPI Python backend
- `evm/` — Solidity smart contracts (Foundry)

The core flow: sellers upload AES-encrypted datasets to IPFS and create on-chain listings; buyers purchase via smart contract; the backend verifies on-chain access and releases the decryption key.

## Commands

### Client (`client/`)
```bash
npm run dev        # Start dev server (http://localhost:5173)
npm run build      # TypeScript check + production build
npm run lint       # ESLint
npm run preview    # Preview production build
```

### Mobile (`mobile/`)
```bash
npx expo start     # Start Expo dev server
npm run lint       # ESLint
```

### Server (`server/`)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pytest                                                    # All tests
pytest tests/services/test_contract_service.py -q        # Single test file
pytest -k "test_name" -q                                  # Single test by name
```

### Smart Contracts (`evm/`)
```bash
make anvil           # Start local Anvil node (port 8545, chain ID 31337)
make deploy-anvil    # Deploy Marketplace contract
make seed-anvil      # Seed test data
make build           # Compile contracts + export ABI to server/app/contracts/
forge test           # Run Solidity tests
forge fmt            # Format Solidity files
```

### Dev Environment
```bash
tilt up     # Start full stack (requires Minikube + Docker)
tilt down   # Stop all services
```

## Architecture

### Client
- **Routing**: React Router DOM with pages in `src/pages/`
- **State**: Zustand stores in `src/stores/` (wallet, theme, currency, search, upload). Wallet state is persisted to localStorage via Zustand's persist middleware.
- **Web3**: Direct MetaMask integration via `window.ethereum` and Ethers.js 6
- **Bootstrap**: `src/bootstrap/app-bootstrap.tsx` handles app initialization
- **Path alias**: `@/*` maps to `src/*`

### Server
Layered FastAPI architecture: **Routers → Services → Models/Schemas**

- `app/routers/` — Route handlers; use FastAPI `Depends()` for service injection
- `app/services/` — Business logic (AI ranking, LLM embedding, contract reads, encryption, IPFS)
- `app/schemas/` — Pydantic request/response models
- `app/models/` — SQLModel database models (PostgreSQL)
- `app/config/settings.py` — All config via Pydantic `BaseSettings` with env var aliases; copy `server/.env.example` → `server/.env`

Key API endpoints (base: `http://localhost:8000`):
- `/api/v1/llm/embed/batch` — Batch embedding pipeline for datasets
- `/api/v1/ai/similarity-search` — Semantic ranking against marketplace listings
- `/api/v1/contract/items/*` — Read on-chain marketplace state
- `/api/v1/datasets/{listing_id}/key` — Decrypt key release (gated by on-chain purchase verification)

### Smart Contracts
Single contract (`evm/src/Marketplace.sol`) handles all marketplace logic:
- OpenZeppelin `Ownable` + `ReentrancyGuard`
- Fee model: basis points (bps) with configurable recipient
- Metadata freezes after first purchase to preserve integrity
- After `make build`, ABI is exported to `server/app/contracts/`

### Mobile
Expo Router with file-based routing under `mobile/app/`. Currently has tab navigation (`(tabs)/`) with Home and Explore screens.

## Environment Setup

- **Client/Mobile**: Node.js 20.x
- **Server**: Python 3.11+; requires `.env` from `.env.example`
- **EVM**: Foundry toolchain; requires `.env` from `.env.example` (Anvil RPC URL, private keys, fee config)
- **Full stack**: Docker + Minikube for Tilt-based orchestration

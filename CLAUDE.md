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
npm run start      # Start Expo dev server
npm run ios        # Start iOS target
npm run android    # Start Android target
npm run web        # Start Expo web target
npm run lint       # ESLint
npm run test       # Jest tests
```

### Server (`server/`)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

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

Key API endpoints (base: `http://localhost:8080`):

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

Expo Router with file-based routing under `mobile/src/app/`.

- **Tabs**: Home, Search, Upload, Wallet
- **Marketplace UX**: semantic search, dataset detail route (`/dataset/[id]`), purchase history
- **Wallet**: Reown AppKit + WalletConnect integration for EVM sessions
- **Seller flow**: CSV upload, embedding/encryption job polling, on-chain listing creation
- **State**: Zustand stores (`marketplace`, `search`, `upload`, `wallet`, `currency`)

## Environment Setup

- **Client/Mobile**: Node.js 20.x
- **Server**: Python 3.11+; requires `.env` from `.env.example`
- **EVM**: Foundry toolchain; requires `.env` from `.env.example` (Anvil RPC URL, private keys, fee config)
- **Full stack**: Docker + Minikube for Tilt-based orchestration

## Agent Skills

Skills are located under `.agents/skills/` (shared across agents in this repo).  
Agents **must read the selected skill's `SKILL.md` before implementation** and follow its workflow, constraints, and quality checks.

### Skill Loading Protocol (Required)

1. **Classify the request** by domain (`client/`, `mobile/`, `server/`, `evm/`, docs/copy, debugging, or orchestration).
2. **Load mandatory foundation skills first**:
   - `brainstorming` before creative feature work, behavior changes, or significant refactors.
   - `systematic-debugging` before attempting fixes for bugs, flaky tests, or unknown failures.
3. **Load one or more domain skills** based on touched code.
4. **Compose skills when needed** (foundation + domain + specialist), avoiding conflicting instructions.
5. **Execute and verify** using commands/tests defined in this document.
6. **Report what was used** in the final response (which skills drove decisions and checks).

### Skill Selection Matrix

| Skill                         | Path                                          | Primary trigger                                                                  |
| ----------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------- |
| `api-design-principles`       | `.agents/skills/api-design-principles/`       | API contract design, endpoint semantics, request/response consistency            |
| `brainstorming`               | `.agents/skills/brainstorming/`               | Any new feature, behavior change, or non-trivial redesign before coding          |
| `copywriting`                 | `.agents/skills/copywriting/`                 | Marketing/product copy improvements and messaging                                |
| `e2e-testing-patterns`        | `.agents/skills/e2e-testing-patterns/`        | End-to-end testing strategy, Playwright/Cypress coverage, and flaky E2E fixes    |
| `fastapi-templates`           | `.agents/skills/fastapi-templates/`           | FastAPI route/service scaffolding, dependency injection, API structure           |
| `frontend-design`             | `.agents/skills/frontend-design/`             | UI-heavy pages/components requiring high design quality                          |
| `github-actions-templates`    | `.agents/skills/github-actions-templates/`    | GitHub Actions workflow setup, CI/CD automation, or reusable workflow patterns   |
| `postgresql-table-design`     | `.agents/skills/postgresql-table-design/`     | PostgreSQL schema design: types, indexes, constraints, pgvector                  |
| `python-testing-patterns`     | `.agents/skills/python-testing-patterns/`     | Python test design, fixtures, mocking, and best practices                        |
| `react-state-management`      | `.agents/skills/react-state-management/`      | Zustand/global state refactors in `client/` or `mobile/`                         |
| `requesting-code-review`      | `.agents/skills/requesting-code-review/`      | Final verification pass before merge or when a dedicated review is requested     |
| `shadcn`                      | `.agents/skills/shadcn/`                      | Add, fix, style, or compose shadcn/ui components in `client/`                    |
| `skill-creator`               | `.agents/skills/skill-creator/`               | Create, update, benchmark, or package repository skills                          |
| `solskill`                    | `.agents/skills/solskill/`                    | Solidity/Foundry contract logic, testing, and security-sensitive changes         |
| `subagent-driven-development` | `.agents/skills/subagent-driven-development/` | Multi-track work that can be safely parallelized                                 |
| `systematic-debugging`        | `.agents/skills/systematic-debugging/`        | Bug investigation, failing tests, regressions, or unclear root cause             |
| `terraform-style-guide`       | `.agents/skills/terraform-style-guide/`       | Terraform authoring or review that must follow HashiCorp style conventions       |
| `terraform-test`              | `.agents/skills/terraform-test/`              | Terraform `.tftest.hcl` creation, assertions, mocks, or test troubleshooting     |
| `test-driven-development`     | `.agents/skills/test-driven-development/`     | Feature or bugfix implementation where tests should drive the change             |
| `typescript-advanced-types`   | `.agents/skills/typescript-advanced-types/`   | Complex TS generics, utility types, or type-level constraints                    |
| `vercel-react-best-practices` | `.agents/skills/vercel-react-best-practices/` | `client/` React/Vite changes, performance, rendering, and data-fetching patterns |
| `vercel-react-native-skills`  | `.agents/skills/vercel-react-native-skills/`  | `mobile/` Expo/React Native features, performance, and platform APIs             |
| `writing-plans`               | `.agents/skills/writing-plans/`               | Specs or multi-step implementation plans that should be written before coding     |

## Specs & Planning

Feature specs live in the Obsidian Vault at `/Users/axelsanchez/Code/Obsidian Vault/`.
When a task references a spec, read the relevant vault note before loading any skills.

| Feature                       | Vault Note                                                       |
| ----------------------------- | ---------------------------------------------------------------- |
| Semantic Search refactor      | `/Users/axelsanchez/Code/Obsidian Vault/Semantic Search.md`      |
| CADC payment integration      | `/Users/axelsanchez/Code/Obsidian Vault/CADC.md`                 |
| Backend architecture refactor | `/Users/axelsanchez/Code/Obsidian Vault/Backend Architecture.md` |
| Dataset preview               | `/Users/axelsanchez/Code/Obsidian Vault/Dataset Preview.md`      |

### Recommended Skill Combinations

- **New API endpoint**: `brainstorming` -> `api-design-principles` + `fastapi-templates`
- **API bug/regression**: `systematic-debugging` -> `api-design-principles` (and `fastapi-templates` if structural)
- **Client UI feature**: `brainstorming` -> `frontend-design` + `vercel-react-best-practices` (+ `shadcn` if used)
- **State management changes**: `brainstorming` -> `react-state-management` (+ `typescript-advanced-types` if type-heavy)
- **Mobile feature/perf issue**: `brainstorming` or `systematic-debugging` -> `vercel-react-native-skills`
- **Contract feature/fix**: `brainstorming` or `systematic-debugging` -> `solskill`
- **New backend service + repo + tests**: `brainstorming` -> `fastapi-templates` + `api-design-principles` + `test-driven-development` + `python-testing-patterns`
- **New database table or schema change**: `postgresql-table-design` (always load when writing migrations or SQLModel definitions)
- **Implementation with tests first**: `test-driven-development` + domain skill (`fastapi-templates`, `vercel-react-best-practices`, `vercel-react-native-skills`, or `solskill`)
- **Python backend test work**: `python-testing-patterns` + `fastapi-templates` (+ `systematic-debugging` when fixing regressions)
- **E2E test suite**: `e2e-testing-patterns` + `frontend-design` or `vercel-react-best-practices`
- **CI/CD automation**: `github-actions-templates` (+ `python-testing-patterns`, `e2e-testing-patterns`, or `terraform-test` depending on pipeline scope)
- **Terraform delivery**: `terraform-style-guide` + `terraform-test`
- **Large scoped effort**: `writing-plans` -> `subagent-driven-development` when work can be split safely
- **Pre-merge validation**: primary implementation skills -> `requesting-code-review`

### Agent Optimization Rules

- Prefer the **smallest correct skill set**; do not load unrelated skills.
- If multiple skills apply, prioritize in this order: **safety/debugging -> architecture/design -> framework-specific -> type/perf polish**.
- Re-check skill guidance when task scope expands (for example from UI tweak to state refactor).
- Match verification depth to risk: contract and backend auth/payment paths require stronger validation.
- Prefer `test-driven-development` for implementation work and `writing-plans` when the user provides a spec or the task spans multiple coordinated steps.
- Use `requesting-code-review` before handing off substantial work that is ready for merge or broader review.

### Anti-Patterns (Do Not Do)

- Starting implementation without reading the relevant `SKILL.md`.
- Using only domain skills when debugging is required (skip-root-cause behavior).
- Applying `frontend-design` for purely data/model/backend tasks.
- Overusing `subagent-driven-development` for tightly coupled, sequential edits.
- Skipping test-focused skills on work that clearly changes verification scope (`test-driven-development`, `python-testing-patterns`, `e2e-testing-patterns`, or `terraform-test`).
- Reaching for `github-actions-templates` or `terraform-style-guide` outside CI/IaC work just because those tools are available.

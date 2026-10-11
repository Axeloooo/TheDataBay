# Launch Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship five PRs to `devel` that fix the client build, close the two security holes, add an event indexer, and add "My datasets" and a seller dashboard.

**Architecture:** FastAPI gains an auth module (nonce, signature verify, JWT) and an in-process indexer task that mirrors contract events into Postgres. New `/me/*` endpoints read the indexer tables. Web and mobile gain a lazy sign-in session and two new views each.

**Tech Stack:** FastAPI, SQLModel, Web3.py, eth-account, PyJWT, pytest; React 19 + Vite + vitest; Expo + jest; GitHub Actions; semantic-release.

**Spec:** `docs/superpowers/specs/2026-10-11-launch-readiness-design.md` (copy at `/mnt/project-files/launch-readiness/`).

## Global Constraints

- Branches `feature/short-description` or `fix/short-description`; PRs target `devel`.
- Commits `feat: ...` or `fix: ...`.
- Every PR adds a line under `## Unreleased` in `CHANGELOG.md`.
- PR body starts with the two-line "Requested by" attribution block; no "Generated with Claude Code" footer and no session link.
- API tests: `cd api && pytest` must stay green with coverage >= 55%.
- Never touch `main`, mainnet, or production deploys.
- Wallet types are `evm` and `solana`; Solana sign-in returns HTTP 501 for now.

## Review Focus

- Replayed nonce: second `verify` with the same nonce returns 401 (Task 2.1 test).
- Expired nonce and expired token return 401 (Task 2.1, 2.2 tests).
- Token for wallet A requesting the key for a listing only wallet B bought returns 403 (Task 2.3 test).
- Indexer crash mid-chunk then restart creates no duplicate purchases (Task 3.2 test).
- Wallet with no purchases or listings gets `[]`, not an error (Task 4.1 test).

---

## PR 0: `feature/release-workflow` (Sonnet 5.5, low effort)

### Task 0.1: Changelog, semantic-release plugins, contributing docs, docs tracking
**Files:** Create `CHANGELOG.md`; Modify `.releaserc`, `.github/workflows/release.yml`, `README.md`, `.gitignore`; Add `docs/superpowers/specs/2026-10-11-launch-readiness-design.md` and this plan.
**Interfaces:** Produces: `CHANGELOG.md` with an `## Unreleased` heading that later PRs append to.
- [ ] Add `!docs/superpowers/` style exceptions to `.gitignore` (the file ignores `docs/`; use `docs/*` then `!docs/superpowers/` and `!docs/agentic-layer.md`) and confirm `git status` shows the spec and plan as addable.
- [ ] Add `@semantic-release/changelog` and `@semantic-release/git` to `.releaserc` (assets: `CHANGELOG.md`, message `chore(release): ${nextRelease.version} [skip ci]`) and install them in `release.yml`.
- [ ] Add a "Contributing" section to `README.md`: branch names, commit prefixes, PRs target `devel`, release is a `devel` to `main` PR, then merge `main` back into `devel`.
- [ ] Verify: `python -c "import json;json.load(open('.releaserc'))"` succeeds and `git diff --stat` shows only the files above.
- [ ] Commit `feat: add changelog and release workflow`.

## PR 1: `fix/client-build-and-lockfiles` (Sonnet 5.5, low effort)

### Task 1.1: Green client build and lockfiles
**Files:** Modify `client/tsconfig.app.json`, `client/tsconfig.test.json` (or the test tsconfig that exists), add `client/src/types/ethereum.d.ts` if no declaration exists; regenerate `client/package-lock.json` and `mobile/package-lock.json`; Modify `.github/workflows/test.yml`; Modify `CHANGELOG.md`.
- [ ] Reproduce: `cd client && npm ci` fails and `npm run build` fails on `toBeInTheDocument`.
- [ ] Regenerate both lockfiles with `npm install --package-lock-only` using the Node version in CI; verify `npm ci` passes in `client/` and `mobile/`.
- [ ] Exclude `**/*.test.tsx` and `**/*.test.ts` from `tsconfig.app.json`; add `vite/client` to the test tsconfig `types` and declare `interface Window { ethereum?: unknown }`.
- [ ] Verify: `cd client && npm run lint && npm run build && npx vitest run` all pass; `cd mobile && npm run lint && npm run test` pass.
- [ ] In `test.yml` use `npm ci` and add a client job running lint, build and vitest.
- [ ] Commit `fix: restore client build and sync lockfiles`.

## PR 2: `feature/wallet-auth` (Opus 5.5, high effort)

### Task 2.1: Nonce and signature verification
**Files:** Create `api/app/auth/{__init__,models,service,schemas,router}.py`; Modify `api/app/main.py` (register router), `api/app/config/settings.py` (`auth_jwt_secret: SecretStr`, `auth_token_ttl_seconds: int = 3600`, `auth_nonce_ttl_seconds: int = 300`), `api/requirements.txt` (`PyJWT`); Test `api/tests/unit/auth/test_service.py`.
**Produces:** `AuthNonce` SQLModel (address, wallet_type, nonce, expires_at, used_at); `create_nonce(session, wallet_type, address, settings) -> NonceResponse` (nonce + message); `verify_signature(session, wallet_type, address, signature, settings) -> str` (JWT); endpoints `POST /api/v1/auth/nonce`, `POST /api/v1/auth/verify`.
- [ ] Failing tests: valid EVM `personal_sign` returns a token; reused nonce raises 401; expired nonce raises 401; signature from a different key raises 401; `wallet_type=solana` raises 501.
- [ ] Implement with `eth_account.messages.encode_defunct` and `Account.recover_message`; mark nonce used in the same transaction.
- [ ] Run `pytest tests/unit/auth -q`, expect pass. Commit `feat: add wallet nonce and signature sign-in`.

### Task 2.2: Token dependency
**Files:** Create `api/app/auth/dependencies.py`; Test `api/tests/unit/auth/test_dependencies.py`.
**Produces:** `current_wallet(authorization: str = Header(...), settings) -> AuthedWallet(wallet_type, address, wallet_id: bytes)`; `require_owner(wallet = Depends(current_wallet), settings) -> AuthedWallet` which compares against `contract_service.owner(settings)` case-insensitively and raises 403.
- [ ] Tests: missing, malformed, expired and tampered tokens raise 401; non-owner raises 403; owner passes.
- [ ] Implement; commit `feat: add auth dependencies`.

### Task 2.3: Protect routes and remove ownership routes
**Files:** Modify `api/app/datasets/router.py` (`release_key` uses `current_wallet`, `KeyReleaseRequest.address` removed), `api/app/contracts/router.py` (`grant_access`, `set_fee_config` use `require_owner`; delete `transfer_ownership` and `renounce_ownership` routes and their schemas if unused), `evm/Makefile` or root `Makefile` (add `transfer-ownership-<network>` target note only if a deploy script exists); update existing tests under `api/tests/unit/api/`.
- [ ] Failing tests: key request without token is 401; token for wallet A with only wallet B holding access is 403; wallet with access gets the key; admin routes 401 without token and 403 for non-owner; `/ownership/transfer` and `/ownership/renounce` return 404.
- [ ] Implement and make the full `pytest` suite pass with coverage >= 55%.
- [ ] Commit `feat: require wallet auth for key release and admin routes`.

### Task 2.4: Client and mobile session
**Files:** Create `client/src/stores/session-store.ts`, `client/src/lib/auth.ts`, `mobile/src/stores/session-store.ts`, `mobile/src/lib/auth.ts`; Modify the key-release call sites in `client/src/` and `mobile/src/` to send `Authorization: Bearer` and drop `address` from the body; Tests next to each new file.
**Produces:** `ensureSession(): Promise<string>` returning a valid token, signing in via the connected wallet only when none exists or the token expires within 60s.
- [ ] Tests (vitest and jest): `ensureSession` signs once for two consecutive calls; re-signs after expiry.
- [ ] Implement; run `npm run lint && npm run build && npx vitest run` in `client/` and `npm run lint && npm run test` in `mobile/`.
- [ ] Add `AUTH_JWT_SECRET` to `.env.example` and a note in `infra/DEPLOYMENT.md` for Key Vault. Commit `feat: add wallet session to client and mobile`.

## PR 3: `feature/event-indexer` (Opus 5.5, high effort)

### Task 3.1: Tables and settings
**Files:** Create `api/app/indexer/{__init__,models}.py`; Modify `api/app/config/settings.py` (`indexer_enabled: bool = False`, `indexer_start_block: int = 0`, `indexer_block_chunk: int = 2000`, `indexer_confirmations: int = 2`, `indexer_poll_seconds: int = 5`); Test `api/tests/unit/indexer/test_models.py`.
**Produces:** SQLModels `IndexedListing`, `IndexedPurchase` (unique on tx_hash + log_index), `IndexerState` (name, last_indexed_block).
- [ ] Failing test: inserting the same (tx_hash, log_index) twice raises an integrity error. Implement; commit `feat: add indexer tables`.

### Task 3.2: Log handling and cursor
**Files:** Create `api/app/indexer/service.py`; Test `api/tests/unit/indexer/test_service.py`.
**Produces:** `index_range(session, contract, from_block: int, to_block: int) -> int` (returns rows written; upserts listings/purchases and applies `PriceUpdated`); `run_once(session, settings) -> int` (reads cursor, `latest - confirmations`, chunks, advances cursor in the same transaction).
- [ ] Failing tests with fixture logs: expected rows; replaying the same range creates no duplicates; cursor does not advance when a write raises; nothing happens when `latest - confirmations < cursor`.
- [ ] Implement; commit `feat: index marketplace events`.

### Task 3.3: Background task, lock, read path, health
**Files:** Create `api/app/indexer/runner.py`; Modify `api/app/main.py` (start in `lifespan` when `indexer_enabled`), `api/app/contracts/router.py` and `service.py` (browse and by-wallet purchases read tables, fall back to contract reads when `IndexerState` is missing), `api/app/health/router.py` (`indexer_lag_blocks` in `/health/ready`); Test `api/tests/unit/indexer/test_runner.py`.
**Produces:** `run_forever(settings)` using `pg_try_advisory_lock(<constant>)`; replicas that fail to take the lock sleep and retry.
- [ ] Failing tests: second runner does not index while the first holds the lock; browse endpoint returns table rows when state exists and contract rows otherwise; readiness includes lag.
- [ ] Implement; `pytest` full suite green. Commit `feat: run indexer and serve reads from Postgres`.

## PR 4: `feature/my-datasets-and-seller-dashboard` (Sonnet 5.5, medium effort; starts after PR 2 and PR 3 are merged to `devel`)

### Task 4.1: `/me` endpoints
**Files:** Create `api/app/me/{__init__,router,service,schemas}.py`; Modify `api/app/main.py`; Test `api/tests/unit/api/test_me.py`.
**Produces:** `GET /api/v1/me/purchases -> list[PurchasedListing]`; `GET /api/v1/me/listings -> list[SellerListing(listing_id, price, payment_token, sales_count, earnings_by_token: dict[str,str], price_editable: bool)]`. Both use `current_wallet`.
- [ ] Failing tests: seeded tables return the wallet's rows only; wallet with none returns `[]`; no token returns 401; `price_editable` is false after the first sale.
- [ ] Implement; commit `feat: add my purchases and seller listings endpoints`.

### Task 4.2: Web pages
**Files:** Create `client/src/pages/MyDatasets.tsx`, `client/src/pages/SellerDashboard.tsx`, tests next to each; Modify router and `Layout` nav.
- [ ] Failing vitest tests: empty state, list rendering, price edit disabled for sold listings. Implement with existing shadcn components; reuse the key and decrypt flow from `DatasetDetail`. Commit `feat: add my datasets and seller dashboard pages`.

### Task 4.3: Mobile screens
**Files:** Create `mobile/src/app/(tabs)/my-datasets.tsx`, `mobile/src/app/(tabs)/seller.tsx` (or under wallet), hooks and jest tests.
- [ ] Failing jest tests for the data hooks (loading, empty, error). Implement; `npm run lint && npm run test` pass. Update `CHANGELOG.md`. Commit `feat: add my datasets and seller screens`.

## Execution

- Dispatch order: PR 0 and PR 1 in parallel (separate worktrees), PR 2 and PR 3 in parallel (separate worktrees), PR 4 after both merge.
- After each implementor reports, I run the repo checks myself, open a draft PR to `devel`, then dispatch a reviewer (Sonnet 5.5 for PR 0, 1, 4; Opus 5.5 for PR 2, 3). Approved and green PRs are merged to `devel`; nothing is merged to `main`.

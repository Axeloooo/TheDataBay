# Launch readiness: security, indexer, buyer and seller pages

Status: draft for review. Date: 2026-10-11. Based on `devel` at f74372c.

## Goal

Get TheDataBay to a safe, demo-able launch on Base Sepolia. Two security holes are closed, the client and mobile builds are green in CI, and buyers and sellers can see what they own and sell.

Agreed with Axel in the brainstorming thread:
- Priority is a safe, demo-able launch before growing the product surface.
- Admin routes are protected by owner-wallet sign-in, not a shared API key.
- Buyers sign in once per session and reuse a short-lived token.
- The event indexer runs as a background task inside the FastAPI app.

Out of scope for this round: ratings and reviews, dataset versioning, OpenAI provider tests. They stay in `/mnt/project-files/feature-ideas/feature-ideas.md`.

## Repository conventions (apply to every PR below)

- Branches: `feature/short-description` and `fix/short-description`. Work PRs target `devel`.
- Commits: `feat: ...` and `fix: ...`.
- Releases: a PR from `devel` to `main`. `release.yml` runs semantic-release on `main`.
- Every PR adds a line under `## Unreleased` in `CHANGELOG.md`.
- After each release, `main` is merged back into `devel` so the changelog commit made on `main` is synced.
- Current state: `devel` holds all history; `main` is one commit ("feat: Repository setup"). The first release PR will therefore be large.

## PR 0: Release workflow (`feature/release-workflow`)

- Add `CHANGELOG.md` with an `## Unreleased` section.
- Extend `.releaserc` with `@semantic-release/changelog` and `@semantic-release/git` so each release writes the changelog and commits it to `main`.
- Update `release.yml` to install those plugins and grant `contents: write`.
- Add a short "Contributing" section to `README.md` with the branch, commit and release rules above, including the post-release sync of `devel`.

## PR 1: Make the build green (`fix/client-build-and-lockfiles`)

Findings from the health check:
- `npm run build` in `client/` fails: `tsc -b` compiles `src/components/record-card.test.tsx` without jest-dom types, and the test tsconfig lacks `vite/client` and a `window.ethereum` declaration.
- `npm ci` fails in `client/` and `mobile/` because the lockfiles are out of sync. `infra/docker/production/client.Dockerfile` uses `npm ci`.
- `.github/workflows/test.yml` never runs the client or `npm run build`.

Changes:
1. Regenerate both lockfiles with the repo's Node version.
2. Exclude `*.test.tsx` from `tsconfig.app.json`; add `vite/client` types and a `Window.ethereum` declaration to the test tsconfig.
3. In `test.yml`: switch to `npm ci`, add a client job running lint, `npm run build` and vitest.

Acceptance: `npm ci && npm run build` passes in `client/`; `npm ci` passes in `mobile/`; the new CI job is green.

## PR 2: Wallet sign-in and locked-down admin (`feature/wallet-auth`)

Wallets in this codebase are typed (`WalletType` is `evm` or `solana`, see `contracts/service.py:wallet_id`), so sign-in has to handle both.

**Flow**
1. `POST /api/v1/auth/nonce` with `{wallet_type, address}` returns a one-time nonce and the exact message to sign (domain, address, nonce, expiry).
2. `POST /api/v1/auth/verify` with `{wallet_type, address, signature}` verifies the signature and returns a short-lived bearer token (default 1 hour, `AUTH_TOKEN_TTL_SECONDS`).
3. Nonces are stored in Postgres (`auth_nonces`: address, nonce, expires_at, used_at), single use, 5 minute expiry.
4. Tokens are HS256 JWTs signed with a new `AUTH_JWT_SECRET` setting. Claims: wallet type, address, wallet id.

**Signature verification**
- EVM: `personal_sign`, verified with `eth_account` (already in `requirements.txt`).
- Solana: ed25519, verified with PyNaCl (new dependency). Decision to confirm during implementation: if Solana buyers cannot currently get access on-chain, ship EVM first and return 501 for Solana sign-in rather than leave it half-working.

**Protected routes**
- `POST /datasets/{id}/key`: requires a valid token; the token's wallet must pass the existing `hasAccess` check. The `address` field in the request body is removed; the token is the identity.
- `POST /items/{id}/grant-access`, `PATCH /fee-config`: require a token whose wallet equals the contract `owner()`.
- `POST /ownership/transfer` and `POST /ownership/renounce`: removed from the HTTP API. Remaining path is a Makefile target in `evm/`.

**Clients**
- Web and mobile stores gain a `session` (token, expiry, address). A "sign in" step runs lazily the first time a protected call is made, then reuses the token until expiry.
- Key release and any admin UI call the API with `Authorization: Bearer`.

**Tests (pytest):** nonce single-use and expiry; wrong signer rejected; token for wallet A cannot fetch the key for a listing only wallet B bought; non-owner token gets 403 on admin routes; removed routes return 404.

## PR 3: Event indexer (`feature/event-indexer`)

**Tables** (SQLModel, created on startup like the existing ones)
- `listings`: listing_id (unique), seller, payment_token, price, dataset_url, created_block, frozen, updated_at.
- `purchases`: tx_hash + log_index (unique together), listing_id, buyer, payment_token, price_paid, fee_paid, seller_paid, block_number, block_time.
- `indexer_state`: name, last_indexed_block.

**Worker**
- Started from `lifespan` in `main.py` as an asyncio task, only when `INDEXER_ENABLED=true`.
- Each tick reads logs for `ItemCreated`, `ItemPurchased` and `PriceUpdated` from `last_indexed_block + 1` to `latest - CONFIRMATIONS`, in chunks of `INDEXER_BLOCK_CHUNK`, then upserts rows and advances `last_indexed_block` in the same transaction. Inserts are idempotent so a crash mid-chunk is safe.
- A Postgres advisory lock ensures only one replica indexes at a time.
- First run starts at `INDEXER_START_BLOCK` (the deploy block) to avoid scanning from genesis.

**Read path**
- Existing browse endpoints (`/contract/items/all` and by-wallet purchases) read from `listings` and `purchases`, and fall back to direct contract reads when the indexer has never run.
- `GET /health/ready` reports indexer lag in blocks.

**Tests:** log fixtures run through the handler produce expected rows; replaying the same logs creates no duplicates; the cursor only advances after a successful write; the lock prevents a second indexer.

## PR 4: My datasets and seller dashboard (`feature/my-datasets-and-seller-dashboard`)

**API** (both require the PR 2 token; the wallet comes from the token)
- `GET /api/v1/me/purchases`: purchased listings with metadata and purchase time.
- `GET /api/v1/me/listings`: the wallet's listings with sale count and earnings per payment token (sum of `seller_paid`), plus whether the price is still editable (no sales yet).
- Price edits reuse the existing `updatePrice` flow and are rejected once a listing has sales.

**Web (`client/`):** a "My datasets" page (list, re-download and decrypt using the existing key flow) and a "Seller dashboard" page (listings table, earnings per token, inline price edit while unsold). Route and nav entries added in `Layout`.

**Mobile (`mobile/`):** matching "My datasets" and "Seller" screens under the tabs/wallet area, sharing the API client.

**Tests:** API tests with seeded indexer tables; vitest component tests for both pages; jest tests for the mobile screens' data hooks.

## Execution and review

- Each PR is built by a dispatched implementor subagent working from the written plan.
  - PR 0, PR 1: Sonnet 5.5, low effort (mechanical config and CI work).
  - PR 2, PR 3: Opus 5.5, high effort (security-sensitive and architectural).
  - PR 4: Sonnet 5.5, medium effort (UI and straightforward queries on top of PR 2 and PR 3).
- I review each result before opening the PR, and PRs follow the existing open-PR policy (a reviewer is dispatched per PR).
- Order: PR 0 and PR 1 first (independent, either order), then PR 2, then PR 3, then PR 4. PR 4 depends on both PR 2 and PR 3.

## Risks and open items

- Production secrets: `AUTH_JWT_SECRET` must be added to Key Vault and the k8s secret provider class before PR 2 deploys.
- The indexer runs in each backend replica; the advisory lock makes that safe, but if the backend scales out heavily it should move to its own deployment.
- Solana sign-in support is conditional, as described in PR 2.
- The first `devel` to `main` release will be a large diff because `main` has a single commit.

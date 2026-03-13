# BridgeMart Mobile

Expo + React Native mobile app for the BridgeMart decentralized dataset marketplace.

## Features

| Feature | Status |
|---------|--------|
| Marketplace feed (browse datasets) | ✅ Implemented |
| Dataset detail view | ✅ Implemented |
| Semantic search | ✅ Implemented |
| Wallet / Account screen | ✅ Implemented |
| Purchased datasets list | ✅ Implemented |
| Key release + CSV download | ✅ Implemented |
| Dataset integrity verification | ✅ Implemented |
| FX rate display (ETH/USD/CAD/EUR) | ✅ Implemented |
| Deep linking (`mobile://dataset/:id`) | ✅ Implemented |
| On-chain buy transaction | ✅ Implemented (via `buyItemTx`; WalletConnect required) |
| Dataset upload flow | ✅ Implemented |

## Running the App

### Prerequisites

- Node.js 20+
- Expo CLI (`npm install -g expo-cli`)
- Expo Go app on your device, or an iOS/Android simulator
- The BridgeMart backend running at `http://localhost:8080`

### Install Dependencies

```bash
cd mobile
npm install
```

### Configure Environment

Environment is configured via `mobile/app.config.ts` using the `expo.extra` keys that are read by `constants/env.ts`. For development, defaults should work out of the box:

- `expo.extra.apiUrl` – backend API base URL (defaults to `http://localhost:8080`)
- `expo.extra.pinataGatewayUrl` – IPFS gateway base URL (defaults to `https://gateway.pinata.cloud`)

These values are typically sourced from `.env` / process environment in `app.config.ts`. Refer to that file if you need to see or change the defaults.

To point to a different backend (e.g. when running on a physical device), update the `apiUrl` value (either in your `.env` file or directly in `app.config.ts`) to your machine's local IP, for example:

```text
API_URL=http://192.168.1.x:8080
```

or the equivalent change to `expo.extra.apiUrl` in `mobile/app.config.ts`.
```

### Start the Dev Server

```bash
# Start Expo dev server
npx expo start

# Then press:
# i  → open in iOS Simulator
# a  → open in Android Emulator
# Scan QR → open in Expo Go on device
```

### Run Tests

```bash
npm test
```

### Lint

```bash
npm run lint
```

## Architecture

### Navigation (Expo Router)

```
src/app/
  _layout.tsx          Root stack + StoreBootstrap (FX polling, cache warm)
  (tabs)/
    _layout.tsx        4 tabs: Home, Search, Upload, Wallet
    index.tsx          Home feed (featured & recent datasets, pull-to-refresh)
    search.tsx         Semantic search via AI similarity endpoint
    upload.tsx         Dataset upload flow
    wallet.tsx         Wallet connection, purchases, currency picker
  dataset/
    [id].tsx           Dataset detail + integrity check + key release + download
  +not-found.tsx       404 fallback
```

### State Management (Zustand)

All global state is in `stores/`:

| Store | Persisted | Description |
|-------|-----------|-------------|
| `wallet-store.ts` | AsyncStorage | Wallet address, connection state |
| `marketplace-store.ts` | No | Items list with 60s TTL cache |
| `search-store.ts` | No | Query and results state |
| `currency-store.ts` | AsyncStorage | Preferred display currency, FX rates |

### API Integration

`lib/backend.ts` wraps all backend endpoints. Base URL is configured via `constants/env.ts` from `app.json`.

Key endpoints used:
- `GET /api/v1/contract/items/all` — marketplace feed
- `GET /api/v1/contract/items/:id` — dataset detail
- `POST /api/v1/ai/similarity-search` — semantic search
- `POST /api/v1/contract/access/:id/check` — access verification
- `POST /api/v1/contract/purchases/by-wallet` — purchased datasets
- `POST /api/v1/datasets/:id/key` — key release for download

### Wallet Layer

The wallet uses a pluggable adapter pattern (`wallet/adapter.ts`). Currently uses `StubAdapter` which accepts a manually entered EVM address.

To add WalletConnect:
1. Install `@reown/appkit-react-native`
2. Implement `WalletAdapter` in `wallet/walletconnect-adapter.ts`
3. Replace `stubAdapter` import in screens

### Deep Links

Scheme: `mobile://` (configured in `app.json`)

```bash
# Test deep link to dataset detail
npx uri-scheme open "mobile://dataset/0xABCD..." --ios
```

## Directory Structure

```
mobile/
  app/              Expo Router screens
  components/       Reusable UI components
  constants/        App constants (theme, env config)
  hooks/            Custom React hooks
  lib/              Pure utilities (API, crypto, FX, IDs, IPFS)
  stores/           Zustand state stores
  types/            TypeScript type definitions
  wallet/           Wallet adapter interface and stub implementation
  __tests__/        Unit and store tests
```

## Intentionally Deferred

- **On-chain buy transactions** — Requires WalletConnect v2. The Buy button shows an informational alert.
- **Dataset upload** — Requires `expo-document-picker` + real wallet. Use the web app (`client/`).
- **AES-GCM decryption on old Android** — Uses `crypto.subtle` (Hermes). Fallback seam documented in `lib/crypto.ts`.

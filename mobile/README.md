# BridgeMart Mobile

Expo + React Native mobile app for the BridgeMart decentralized dataset marketplace.

## Features

| Feature                               | Status                                                   |
| ------------------------------------- | -------------------------------------------------------- |
| Marketplace feed (browse datasets)    | ✅ Implemented                                           |
| Dataset detail view                   | ✅ Implemented                                           |
| Semantic search                       | ✅ Implemented                                           |
| Wallet / Account screen               | ✅ Implemented                                           |
| Purchased datasets list               | ✅ Implemented                                           |
| Key release + CSV download            | ✅ Implemented                                           |
| Dataset integrity verification        | ✅ Implemented                                           |
| FX rate display (ETH/USD/CAD/EUR)     | ✅ Implemented                                           |
| Deep linking (`mobile://dataset/:id`) | ✅ Implemented                                           |
| On-chain buy transaction              | ✅ Implemented (via `buyItemTx`; WalletConnect required) |
| Dataset upload flow                   | ✅ Implemented                                           |

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

| Store                  | Persisted    | Description                          |
| ---------------------- | ------------ | ------------------------------------ |
| `wallet-store.ts`      | AsyncStorage | Wallet address, connection state     |
| `marketplace-store.ts` | No           | Items list with 60s TTL cache        |
| `search-store.ts`      | No           | Query and results state              |
| `currency-store.ts`    | AsyncStorage | Preferred display currency, FX rates |

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

The wallet is integrated via Reown AppKit and a persisted Zustand wallet store.

- Reown AppKit configuration lives in `src/lib/appkit.tsx`.
- Wallet/account state is managed in a persisted Zustand store under `stores/`.
- Screens read and update wallet state through this store rather than a manual stub adapter.

## Directory Structure

```
mobile/
  app.config.ts     Expo app configuration (expo.extra env wiring)
  assets/           Static app assets (images, icons)
  scripts/          Utility scripts (e.g., reset project)
  src/
    app/            Expo Router screens and route groups
    components/     Reusable UI components
    constants/      App constants (theme, env)
    hooks/          Custom React hooks
    lib/            Utilities (API, crypto, FX, IDs, IPFS, AppKit)
    stores/         Zustand state stores
    types/          TypeScript type definitions
  tests/
    lib/            Unit tests for utility modules
    stores/         Store behavior tests
```

## Limitations and Caveats

- **On-chain buy transactions** — Implemented via Reown AppKit + WalletConnect v2 (`buyItemTx`), but advanced wallet features (e.g. custom gas controls) are still easier to use in the web app.
- **Dataset upload** — Implemented using `expo-document-picker` together with the connected wallet. For large files or advanced options, prefer the web app (`client/`).
- **AES-GCM decryption on old Android** — Uses `crypto.subtle` (Hermes). Fallback seam documented in `lib/crypto.ts`.

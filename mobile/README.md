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

Environment is configured in `app.json` under `expo.extra`. For development defaults work out of the box:

```json
{
  "expo": {
    "extra": {
      "apiUrl": "http://localhost:8080",
      "pinataGatewayUrl": "https://gateway.pinata.cloud"
    }
  }
}
```

To point to a different backend (e.g. on a physical device), update `apiUrl` to your machine's local IP:

```json
"apiUrl": "http://192.168.1.x:8080"
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
app/
  _layout.tsx          Root stack + StoreBootstrap (FX polling, cache warm)
  (tabs)/
    _layout.tsx        3 tabs: Marketplace, Search, Wallet
    index.tsx          Marketplace feed (FlatList, pull-to-refresh)
    search.tsx         Semantic search via AI similarity endpoint
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

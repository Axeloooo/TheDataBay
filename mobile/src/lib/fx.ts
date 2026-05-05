import AsyncStorage from "@react-native-async-storage/async-storage";
import { formatUnits } from "ethers";

export type DisplayCurrency =
  | "ETH"
  | "CAD"
  | "USD"
  | "EUR"
  | "MXN"
  | "USDC"
  | "SOL"
  | "CNY"
  | "USDT";

export type FxRates = {
  ethUsd: number;
  ethCad: number;
  ethEur: number;
  ethMxn: number;
  ethUsdc: number;
  ethSol: number;
  ethCny: number;
  ethUsdt: number;
  usdcUsd: number;
  updatedAt: number;
};

const FX_CACHE_KEY = "thedatabay_fx_rates_v1";
const DEFAULT_TTL_MS = 60_000;

export async function fetchFxRates(): Promise<FxRates> {
  const response = await fetch(
    "https://api.coingecko.com/api/v3/simple/price?ids=ethereum,solana,usd-coin&vs_currencies=usd,cad,eur,mxn,cny",
  );
  if (!response.ok) {
    throw new Error(`FX request failed (${response.status})`);
  }

  const data = (await response.json()) as {
    ethereum?: {
      usd?: number;
      cad?: number;
      eur?: number;
      mxn?: number;
      cny?: number;
    };
    solana?: { usd?: number };
    "usd-coin"?: { usd?: number };
  };

  const ethUsd = data.ethereum?.usd ?? 0;
  const ethCad = data.ethereum?.cad ?? 0;
  const ethEur = data.ethereum?.eur ?? 0;
  const ethMxn = data.ethereum?.mxn ?? 0;
  const ethCny = data.ethereum?.cny ?? 0;
  const solUsd = data.solana?.usd ?? 0;
  const usdcUsd = data["usd-coin"]?.usd ?? 1;

  if (ethUsd <= 0 || ethCad <= 0 || ethEur <= 0 || ethMxn <= 0 || ethCny <= 0) {
    throw new Error("FX payload missing ETH rates");
  }

  const rates: FxRates = {
    ethUsd,
    ethCad,
    ethEur,
    ethMxn,
    ethUsdc: usdcUsd > 0 ? ethUsd / usdcUsd : ethUsd,
    ethSol: solUsd > 0 ? ethUsd / solUsd : 0,
    ethCny,
    ethUsdt: ethUsd,
    usdcUsd: usdcUsd > 0 ? usdcUsd : 1,
    updatedAt: Date.now(),
  };

  await AsyncStorage.setItem(FX_CACHE_KEY, JSON.stringify(rates)).catch(
    () => undefined,
  );
  return rates;
}

export async function loadCachedFxRates(
  maxAgeMs: number = DEFAULT_TTL_MS,
): Promise<FxRates | null> {
  try {
    const raw = await AsyncStorage.getItem(FX_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as FxRates;
    if (!parsed.updatedAt) return null;
    if (Date.now() - parsed.updatedAt > maxAgeMs) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function convertSettlementToCurrency(
  settlementAtomic: string | bigint,
  settlementDecimals: number,
  currency: DisplayCurrency,
  rates: FxRates | null,
): number | null {
  let settlementAmount: number;

  try {
    settlementAmount = Number(
      formatUnits(settlementAtomic, settlementDecimals),
    );
  } catch {
    return null;
  }

  if (!Number.isFinite(settlementAmount)) return null;
  if (currency === "USDC") return settlementAmount;
  if (!rates || rates.ethUsd <= 0) return null;

  const settlementUsd = settlementAmount * rates.usdcUsd;

  switch (currency) {
    case "ETH":
      return settlementUsd / rates.ethUsd;
    case "USD":
      return settlementUsd;
    case "CAD":
      return settlementUsd * (rates.ethCad / rates.ethUsd);
    case "EUR":
      return settlementUsd * (rates.ethEur / rates.ethUsd);
    case "MXN":
      return settlementUsd * (rates.ethMxn / rates.ethUsd);
    case "SOL":
      return rates.ethSol > 0
        ? settlementUsd * (rates.ethSol / rates.ethUsd)
        : null;
    case "CNY":
      return settlementUsd * (rates.ethCny / rates.ethUsd);
    case "USDT":
      return settlementUsd;
    default:
      return null;
  }
}

export function formatCurrencyAmount(
  value: number,
  currency: DisplayCurrency,
): string {
  if (
    currency === "ETH" ||
    currency === "USDC" ||
    currency === "SOL" ||
    currency === "USDT"
  ) {
    const formatted = value.toLocaleString("en-US", {
      maximumFractionDigits: 4,
    });
    return `${formatted} ${currency}`;
  }
  // Intl.NumberFormat is available in React Native's Hermes
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

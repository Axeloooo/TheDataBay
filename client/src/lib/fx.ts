export type DisplayCurrency = "ETH" | "CAD" | "USD" | "EUR" | "USDC" | "SOL";

export type FxRates = {
  ethUsd: number;
  ethCad: number;
  ethEur: number;
  ethUsdc: number;
  ethSol: number;
  updatedAt: number;
};

const FX_CACHE_KEY = "bridgemart_fx_rates_v1";
const DEFAULT_TTL_MS = 60_000;

export async function fetchFxRates(): Promise<FxRates> {
  const response = await fetch(
    "https://api.coingecko.com/api/v3/simple/price?ids=ethereum,solana,usd-coin&vs_currencies=usd,cad,eur",
  );
  if (!response.ok) {
    throw new Error(`FX request failed (${response.status})`);
  }

  const data = (await response.json()) as {
    ethereum?: { usd?: number; cad?: number; eur?: number };
    solana?: { usd?: number };
    "usd-coin"?: { usd?: number };
  };

  const ethUsd = data.ethereum?.usd ?? 0;
  const ethCad = data.ethereum?.cad ?? 0;
  const ethEur = data.ethereum?.eur ?? 0;
  const solUsd = data.solana?.usd ?? 0;
  const usdcUsd = data["usd-coin"]?.usd ?? 1;

  if (ethUsd <= 0 || ethCad <= 0 || ethEur <= 0) {
    throw new Error("FX payload missing ETH rates");
  }

  const rates: FxRates = {
    ethUsd,
    ethCad,
    ethEur,
    ethUsdc: usdcUsd > 0 ? ethUsd / usdcUsd : ethUsd,
    ethSol: solUsd > 0 ? ethUsd / solUsd : 0,
    updatedAt: Date.now(),
  };

  localStorage.setItem(FX_CACHE_KEY, JSON.stringify(rates));
  return rates;
}

export function loadCachedFxRates(maxAgeMs: number = DEFAULT_TTL_MS): FxRates | null {
  try {
    const raw = localStorage.getItem(FX_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as FxRates;
    if (!parsed.updatedAt) return null;
    if (Date.now() - parsed.updatedAt > maxAgeMs) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function convertEthToCurrency(
  ethAmount: number,
  currency: DisplayCurrency,
  rates: FxRates | null,
): number | null {
  if (!Number.isFinite(ethAmount)) return null;
  if (currency === "ETH") return ethAmount;
  if (!rates) return null;

  switch (currency) {
    case "USD":
      return ethAmount * rates.ethUsd;
    case "CAD":
      return ethAmount * rates.ethCad;
    case "EUR":
      return ethAmount * rates.ethEur;
    case "USDC":
      return ethAmount * rates.ethUsdc;
    case "SOL":
      return rates.ethSol > 0 ? ethAmount * rates.ethSol : null;
    default:
      return null;
  }
}

export function formatCurrencyAmount(
  value: number,
  currency: DisplayCurrency,
): string {
  if (currency === "ETH" || currency === "USDC" || currency === "SOL") {
    return `${value.toLocaleString(undefined, {
      maximumFractionDigits: 4,
    })} ${currency}`;
  }

  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

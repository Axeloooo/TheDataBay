export type DisplayCurrency =
  | "USDC"
  | "USD"
  | "CAD"
  | "MXN"
  | "EUR"
  | "ETH"
  | "SOL"
  | "CNY"
  | "USDT";

export type DisplayCurrencyOption = {
  code: DisplayCurrency;
  icon: string;
};

export const DISPLAY_CURRENCY_OPTIONS = [
  { code: "USDC", icon: "/usdc-logo.svg" },
  { code: "USD", icon: "/usa-flag.svg" },
  { code: "CAD", icon: "/canada-flag.svg" },
  { code: "MXN", icon: "/mexico-flag.svg" },
  { code: "EUR", icon: "/eu-flag.svg" },
  { code: "ETH", icon: "/eth-logo.svg" },
  { code: "SOL", icon: "/sol-logo.svg" },
  { code: "CNY", icon: "/china-flag.svg" },
  { code: "USDT", icon: "/usdt-logo.svg" },
] as const satisfies readonly DisplayCurrencyOption[];

export type FxRates = {
  ethUsd: number;
  ethCad: number;
  ethEur: number;
  ethMxn: number;
  ethUsdc: number;
  ethSol: number;
  ethCny: number;
  ethUsdt: number;
  updatedAt: number;
};

const FX_CACHE_KEY = "bridgemart_fx_rates_v1";
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
    ethUsdc: usdcUsd > 0 ? ethUsd / usdcUsd : ethUsd,
    ethSol: solUsd > 0 ? ethUsd / solUsd : 0,
    ethMxn,
    ethCny,
    ethUsdt: ethUsd, // USDT ≈ 1 USD
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
    if (
      !parsed.updatedAt ||
      !parsed.ethUsd ||
      !parsed.ethCad ||
      !parsed.ethEur ||
      !parsed.ethMxn ||
      !parsed.ethCny ||
      !parsed.ethUsdc ||
      !parsed.ethSol ||
      !parsed.ethUsdt
    ) {
      return null;
    }
    if (Date.now() - parsed.updatedAt > maxAgeMs) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function convertSettlementToCurrency(
  settlementAmount: number,
  currency: DisplayCurrency,
  rates: FxRates | null,
): number | null {
  if (!Number.isFinite(settlementAmount)) return null;
  if (currency === "USDC") return settlementAmount;
  if (!rates) return null;

  const usdAmount = settlementAmount;

  switch (currency) {
    case "USD":
      return usdAmount;
    case "CAD":
      return usdAmount * (rates.ethCad / rates.ethUsd);
    case "MXN":
      return usdAmount * (rates.ethMxn / rates.ethUsd);
    case "EUR":
      return usdAmount * (rates.ethEur / rates.ethUsd);
    case "ETH":
      return usdAmount / rates.ethUsd;
    case "SOL":
      return rates.ethSol > 0 ? usdAmount * (rates.ethSol / rates.ethUsd) : null;
    case "CNY":
      return usdAmount * (rates.ethCny / rates.ethUsd);
    case "USDT":
      return usdAmount;
    default:
      return null;
  }
}

export function convertEthToCurrency(
  ethAmount: number,
  currency: DisplayCurrency,
  rates: FxRates | null,
): number | null {
  if (!Number.isFinite(ethAmount)) return null;

  // Conversions start from an ETH amount and use ETH-denominated rates.
  switch (currency) {
    case "ETH":
      return ethAmount;
    default:
      if (!rates) return null;
  }

  switch (currency) {
    case "USD":
      return ethAmount * rates.ethUsd;
    case "USDC":
      return ethAmount * rates.ethUsdc;
    case "CAD":
      return ethAmount * rates.ethCad;
    case "MXN":
      return ethAmount * rates.ethMxn;
    case "EUR":
      return ethAmount * rates.ethEur;
    case "SOL":
      return rates.ethSol > 0 ? ethAmount * rates.ethSol : null;
    case "CNY":
      return ethAmount * rates.ethCny;
    case "USDT":
      return ethAmount * rates.ethUsdt;
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

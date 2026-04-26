export type DisplayCurrency =
  | "USDC"
  | "CADC"
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
  { code: "CADC", icon: "/cadc-logo.svg" },
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
  ethCadc: number;
  ethSol: number;
  ethCny: number;
  ethUsdt: number;
  updatedAt: number;
};

const FX_CACHE_KEY = "bridgemart_fx_rates_v1";
const DEFAULT_TTL_MS = 60_000;

export async function fetchFxRates(): Promise<FxRates> {
  const response = await fetch(
    "https://api.coingecko.com/api/v3/simple/price?ids=ethereum,solana,usd-coin,cad-coin&vs_currencies=usd,cad,eur,mxn,cny",
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
    "cad-coin"?: { usd?: number };
  };

  const ethUsd = data.ethereum?.usd ?? 0;
  const ethCad = data.ethereum?.cad ?? 0;
  const ethEur = data.ethereum?.eur ?? 0;
  const ethMxn = data.ethereum?.mxn ?? 0;
  const ethCny = data.ethereum?.cny ?? 0;
  const solUsd = data.solana?.usd ?? 0;
  const usdcUsd = data["usd-coin"]?.usd ?? 1;
  // CADC is pegged 1:1 to CAD; try cad-coin rate, fall back to ethCad
  const cadcUsd = data["cad-coin"]?.usd ?? 0;

  if (ethUsd <= 0 || ethCad <= 0 || ethEur <= 0 || ethMxn <= 0 || ethCny <= 0) {
    throw new Error("FX payload missing ETH rates");
  }

  const rates: FxRates = {
    ethUsd,
    ethCad,
    ethEur,
    ethUsdc: usdcUsd > 0 ? ethUsd / usdcUsd : ethUsd,
    // ethCadc: ETH priced in CADC. CADC ≈ 1 CAD, so use ethCad as fallback.
    ethCadc: cadcUsd > 0 ? ethUsd / cadcUsd : ethCad,
    ethSol: solUsd > 0 ? ethUsd / solUsd : 0,
    ethMxn,
    ethCny,
    ethUsdt: ethUsd, // USDT ≈ 1 USD
    updatedAt: Date.now(),
  };

  localStorage.setItem(FX_CACHE_KEY, JSON.stringify(rates));
  return rates;
}

export function loadCachedFxRates(
  maxAgeMs: number = DEFAULT_TTL_MS,
): FxRates | null {
  try {
    const raw = localStorage.getItem(FX_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as FxRates;
    if (
      !Number.isFinite(parsed.updatedAt) ||
      !Number.isFinite(parsed.ethUsd) ||
      !Number.isFinite(parsed.ethCad) ||
      !Number.isFinite(parsed.ethEur) ||
      !Number.isFinite(parsed.ethMxn) ||
      !Number.isFinite(parsed.ethCny) ||
      !Number.isFinite(parsed.ethUsdc) ||
      !Number.isFinite(parsed.ethCadc) ||
      !Number.isFinite(parsed.ethSol) ||
      !Number.isFinite(parsed.ethUsdt)
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
  settlementCurrency: "USDC" | "CADC" = "USDC",
): number | null {
  if (!Number.isFinite(settlementAmount)) return null;
  // If the display currency matches the settlement currency, no conversion needed.
  if (currency === settlementCurrency) return settlementAmount;
  if (!rates) return null;

  if (settlementCurrency === "CADC") {
    // CADC is pegged 1:1 to CAD; cadAmount is the base for conversions.
    const cadAmount = settlementAmount;
    const cadToUsd = rates.ethUsd / rates.ethCad;
    switch (currency) {
      case "CADC":
        return cadAmount;
      case "USDC":
      case "USD":
        return cadAmount * cadToUsd;
      case "CAD":
        return cadAmount;
      case "MXN":
        return cadAmount * cadToUsd * (rates.ethMxn / rates.ethUsd);
      case "EUR":
        return cadAmount * cadToUsd * (rates.ethEur / rates.ethUsd);
      case "ETH":
        return cadAmount / rates.ethCad;
      case "SOL":
        return rates.ethSol > 0
          ? (cadAmount / rates.ethCad) * rates.ethSol
          : null;
      case "CNY":
        return cadAmount * cadToUsd * (rates.ethCny / rates.ethUsd);
      case "USDT":
        return cadAmount * cadToUsd;
      default:
        return null;
    }
  }

  // Default: settlementCurrency === "USDC", settlementAmount is in USD-equivalent.
  const usdAmount = settlementAmount;

  switch (currency) {
    case "CADC":
      return usdAmount * (rates.ethCad / rates.ethUsd);
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
      return rates.ethSol > 0
        ? usdAmount * (rates.ethSol / rates.ethUsd)
        : null;
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
    case "CADC":
      return ethAmount * rates.ethCadc;
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
    currency === "CADC" ||
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

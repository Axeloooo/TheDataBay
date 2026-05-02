import {
  BrowserProvider,
  Contract,
  Interface,
  formatEther,
  formatUnits,
  getAddress,
  parseEther,
  ZeroAddress,
} from "ethers";
import { walletRuntime } from "@/lib/wallet/runtime";
import { marketplaceAbi } from "@/lib/marketplaceAbi";
import { uuidToBytes32 } from "@/lib/ids";
import type { MarketplaceDataItem, SettlementCurrency } from "@/types/contract";
import { SETTLEMENT_TOKENS } from "@/types/contract";
import { normalizeAtomicString } from "@/lib/atomic";

const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS as
  | string
  | undefined;
const USDC_TOKEN_ADDRESS = import.meta.env.VITE_USDC_TOKEN_ADDRESS as
  | string
  | undefined;
const CADC_TOKEN_ADDRESS = import.meta.env.VITE_CADC_TOKEN_ADDRESS as
  | string
  | undefined;
const errorInterface = new Interface(marketplaceAbi);
const DEFAULT_SETTLEMENT_CURRENCY: SettlementCurrency = "USDC";
const DEFAULT_SETTLEMENT_DECIMALS = 6;

function settlementDecimalsForCurrency(currency: SettlementCurrency): number {
  return SETTLEMENT_TOKENS[currency].decimals;
}
const erc20Abi = [
  "function balanceOf(address owner) view returns (uint256)",
  "function allowance(address owner,address spender) view returns (uint256)",
  "function approve(address spender,uint256 amount) returns (bool)",
];

export type NormalizedMarketplacePrice = {
  priceAtomic: string;
  settlementCurrency: SettlementCurrency;
  settlementDecimals: number;
  settlementAmount: string;
};

function getContractAddress(): string {
  if (!CONTRACT_ADDRESS) {
    throw new Error("Missing VITE_CONTRACT_ADDRESS");
  }
  const normalized = CONTRACT_ADDRESS.trim();
  if (!normalized) {
    throw new Error("VITE_CONTRACT_ADDRESS is empty");
  }
  try {
    return getAddress(normalized);
  } catch {
    throw new Error(`Invalid VITE_CONTRACT_ADDRESS: ${normalized}`);
  }
}

export function getUsdcTokenAddress(): string {
  if (!USDC_TOKEN_ADDRESS) {
    throw new Error("Missing VITE_USDC_TOKEN_ADDRESS");
  }
  const normalized = USDC_TOKEN_ADDRESS.trim();
  if (!normalized) {
    throw new Error("VITE_USDC_TOKEN_ADDRESS is empty");
  }
  try {
    const address = getAddress(normalized);
    if (address === ZeroAddress) {
      throw new Error("VITE_USDC_TOKEN_ADDRESS cannot be zero.");
    }
    return address;
  } catch (error) {
    if (error instanceof Error && error.message.includes("cannot be zero")) {
      throw error;
    }
    throw new Error(`Invalid VITE_USDC_TOKEN_ADDRESS: ${normalized}`);
  }
}

export function getCadcTokenAddress(): string {
  if (!CADC_TOKEN_ADDRESS) {
    throw new Error("Missing VITE_CADC_TOKEN_ADDRESS");
  }
  const normalized = CADC_TOKEN_ADDRESS.trim();
  if (!normalized) {
    throw new Error("VITE_CADC_TOKEN_ADDRESS is empty");
  }
  try {
    const address = getAddress(normalized);
    if (address === ZeroAddress) {
      throw new Error("VITE_CADC_TOKEN_ADDRESS cannot be zero.");
    }
    return address;
  } catch (error) {
    if (error instanceof Error && error.message.includes("cannot be zero")) {
      throw error;
    }
    throw new Error(`Invalid VITE_CADC_TOKEN_ADDRESS: ${normalized}`);
  }
}

export function getUsdcTokenAddressForCurrency(
  currency: SettlementCurrency,
): string {
  switch (currency) {
    case "USDC":
      return getUsdcTokenAddress();
    case "CADC":
      return getCadcTokenAddress();
  }
}

export async function getEvmProvider(): Promise<BrowserProvider> {
  const eip1193 = await walletRuntime.getEip1193Provider();
  return new BrowserProvider(
    eip1193 as ConstructorParameters<typeof BrowserProvider>[0],
  );
}

export async function createItemTx(params: {
  listingId: string;
  title: string;
  description: string;
  seller: string;
  paymentToken: string;
  priceAtomic: string;
  datasetUrl: string;
  datasetHash: string;
  signatureUrl: string;
  signatureHash: string;
}): Promise<string> {
  try {
    const provider = await getEvmProvider();
    const network = await provider.getNetwork();
    const signer = await provider.getSigner();
    const signerAddress = await signer.getAddress();
    if (!isSameAddress(signerAddress, params.seller)) {
      throw new Error("Connected wallet does not match seller address.");
    }
    const paymentToken = getAddress(params.paymentToken);
    if (paymentToken === ZeroAddress) {
      throw new Error("Payment token is not configured.");
    }
    const contractAddress = getContractAddress();
    const code = await provider.getCode(contractAddress);
    if (!code || code === "0x") {
      const chainId = network.chainId?.toString?.() ?? String(network.chainId);
      throw new Error(
        `No contract code found at ${contractAddress} on chain ${chainId}. ` +
          "Check connected wallet network and VITE_CONTRACT_ADDRESS deployment target.",
      );
    }
    const contract = new Contract(contractAddress, marketplaceAbi, signer);
    const itemId = uuidToBytes32(params.listingId);
    if (!/^0x[0-9a-fA-F]{64}$/.test(params.datasetHash)) {
      throw new Error(
        "Invalid dataset hash format. Expected 0x-prefixed 32-byte hex.",
      );
    }
    if (!/^0x[0-9a-fA-F]{64}$/.test(params.signatureHash)) {
      throw new Error(
        "Invalid signature hash format. Expected 0x-prefixed 32-byte hex.",
      );
    }
    console.info("[createItemTx] submit", {
      chainId: network.chainId?.toString?.() ?? String(network.chainId),
      contract: contractAddress,
      seller: signerAddress,
      paymentToken,
      itemId,
      priceAtomic: params.priceAtomic,
      datasetUrl: params.datasetUrl,
      signatureUrl: params.signatureUrl,
    });
    try {
      await contract.createItem.staticCall(
        itemId,
        params.title,
        params.description,
        params.seller,
        paymentToken,
        params.priceAtomic,
        params.datasetUrl,
        params.datasetHash,
        params.signatureUrl,
        params.signatureHash,
      );
    } catch (error) {
      console.error("[createItemTx] preflight revert", error);
      throw new Error(formatEvmError(error, "create item (preflight)"));
    }
    const tx = await contract.createItem(
      itemId,
      params.title,
      params.description,
      params.seller,
      paymentToken,
      params.priceAtomic,
      params.datasetUrl,
      params.datasetHash,
      params.signatureUrl,
      params.signatureHash,
    );
    console.info("[createItemTx] tx sent", tx.hash);
    const receipt = await tx.wait();
    console.info("[createItemTx] tx mined", receipt?.hash ?? tx.hash);
    return receipt?.hash ?? tx.hash;
  } catch (error) {
    console.error("[createItemTx] failed", error);
    throw new Error(formatEvmError(error, "create item"));
  }
}

export async function getFeeBps(): Promise<bigint> {
  const provider = await getEvmProvider();
  const contract = new Contract(getContractAddress(), marketplaceAbi, provider);
  return contract.feeBps();
}

export async function buyItemTx(
  listingIdBytes32: string,
  priceAtomic: bigint,
  usdcTokenAddress: string,
): Promise<string> {
  try {
    const provider = await getEvmProvider();
    const signer = await provider.getSigner();
    const contractAddress = getContractAddress();
    const contract = new Contract(contractAddress, marketplaceAbi, signer);
    const feeBps = await contract.feeBps();
    const fee = (priceAtomic * BigInt(feeBps)) / 10_000n;
    const total = priceAtomic + fee;
    const paymentToken = getAddress(usdcTokenAddress);
    if (paymentToken === ZeroAddress) {
      throw new Error("Marketplace payment token is not configured.");
    }

    const token = new Contract(paymentToken, erc20Abi, signer);
    const buyerAddress = await signer.getAddress();
    const balance = (await token.balanceOf(buyerAddress)) as bigint;
    if (balance < total) {
      throw new Error("Insufficient token balance for this purchase.");
    }
    const allowance = (await token.allowance(
      buyerAddress,
      contractAddress,
    )) as bigint;

    console.info("[buyItemTx] submit", {
      contract: contractAddress,
      paymentToken,
      buyer: buyerAddress,
      listingIdBytes32,
      priceAtomic: priceAtomic.toString(),
      fee: fee.toString(),
      total: total.toString(),
    });

    if (allowance < total) {
      // Safer approval strategy for USDT-like tokens that may require resetting allowance to 0 first.
      // Check if we have an existing non-zero allowance that needs to be reset.
      if (allowance > 0n) {
        const resetTx = await token.approve(contractAddress, 0n);
        console.info("[buyItemTx] resetting allowance", resetTx.hash);
        await resetTx.wait();
        console.info("[buyItemTx] allowance reset", resetTx.hash);
      }
      const approvalTx = await token.approve(contractAddress, total);
      console.info("[buyItemTx] approval sent", approvalTx.hash);
      await approvalTx.wait();
      console.info("[buyItemTx] approval mined", approvalTx.hash);
    }

    const tx = await contract.buyItem(listingIdBytes32);
    console.info("[buyItemTx] tx sent", tx.hash);
    const receipt = await tx.wait();
    return receipt?.hash ?? tx.hash;
  } catch (error) {
    throw new Error(formatEvmError(error, "buy item"));
  }
}

export function weiToEth(wei: string | number | bigint): string {
  try {
    return formatEther(wei);
  } catch {
    return "0";
  }
}

export function ethToWeiString(eth: string): string {
  try {
    return parseEther(eth).toString();
  } catch {
    return "0";
  }
}

export function isSameAddress(a?: string | null, b?: string | null): boolean {
  if (!a || !b) return false;
  return a.toLowerCase() === b.toLowerCase();
}

export function listingIdFromItem(item: MarketplaceDataItem): string {
  return item.id;
}

function normalizeDecimals(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0 || parsed > 18) {
    return DEFAULT_SETTLEMENT_DECIMALS;
  }
  return parsed;
}

function trimTrailingZeroes(value: string): string {
  if (!value.includes(".")) return value;
  return value
    .replace(/\.0+$/, "")
    .replace(/(\.\d*?[1-9])0+$/, "$1")
    .replace(/\.$/, "");
}

export function formatAtomicAmount(
  amountAtomic: string | number | bigint,
  decimals: number,
): string {
  try {
    return trimTrailingZeroes(formatUnits(amountAtomic, decimals));
  } catch {
    return "0";
  }
}

export function normalizeMarketplacePrice(
  item: Pick<
    MarketplaceDataItem,
    "price_atomic" | "settlement_currency" | "settlement_decimals" | "price"
  >,
): NormalizedMarketplacePrice {
  const priceAtomic = normalizeAtomicString(
    item.price_atomic ?? item.price ?? 0,
  );
  const settlementCurrency: SettlementCurrency =
    item.settlement_currency === "USDC" || item.settlement_currency === "CADC"
      ? item.settlement_currency
      : DEFAULT_SETTLEMENT_CURRENCY;
  const settlementDecimals =
    item.settlement_decimals !== undefined
      ? normalizeDecimals(item.settlement_decimals)
      : settlementDecimalsForCurrency(settlementCurrency);
  return {
    priceAtomic,
    settlementCurrency,
    settlementDecimals,
    settlementAmount: formatAtomicAmount(priceAtomic, settlementDecimals),
  };
}

export function getSettlementDisplayCurrency(
  item: Pick<MarketplaceDataItem, "settlement_currency">,
): SettlementCurrency {
  if (item.settlement_currency === "USDC" || item.settlement_currency === "CADC") {
    return item.settlement_currency;
  }
  return DEFAULT_SETTLEMENT_CURRENCY;
}

function extractErrorData(error: unknown): string | null {
  const anyError = error as {
    data?: unknown;
    error?: { data?: unknown };
    info?: { error?: { data?: unknown } };
  };

  const candidates = [
    anyError?.data,
    anyError?.error?.data,
    anyError?.info?.error?.data,
  ];

  for (const candidate of candidates) {
    if (typeof candidate === "string" && candidate.startsWith("0x")) {
      return candidate;
    }
  }
  return null;
}

function formatEvmError(error: unknown, action: string): string {
  if (error && typeof error === "object") {
    const data = extractErrorData(error);
    if (data) {
      try {
        const parsed = errorInterface.parseError(data);
        if (parsed?.name) {
          return `Failed to ${action}: ${parsed.name}`;
        }
      } catch {
        // ignore parse error
      }
    }
  }

  if (!error || typeof error !== "object") {
    return `Failed to ${action}.`;
  }

  const anyError = error as {
    shortMessage?: string;
    reason?: string;
    message?: string;
  };

  const message =
    anyError.shortMessage ||
    anyError.reason ||
    (typeof anyError.message === "string" ? anyError.message : "");

  const trimmed = message.trim();
  if (trimmed) {
    return `Failed to ${action}: ${trimmed}`;
  }

  try {
    return `Failed to ${action}: ${JSON.stringify(anyError)}`;
  } catch {
    return `Failed to ${action}.`;
  }
}

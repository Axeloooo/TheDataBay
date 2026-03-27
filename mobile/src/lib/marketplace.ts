import {
  BrowserProvider,
  Contract,
  Interface,
  formatUnits,
  getAddress,
  parseUnits,
} from "ethers";

import { ENV } from "@/constants/env";
import { walletRuntime } from "@/src/lib/wallet/runtime";
import { uuidToBytes32 } from "@/src/lib/ids";
import { marketplaceAbi } from "@/src/lib/marketplaceAbi";
import type { MarketplaceDataItem } from "@/src/types/contract";

const errorInterface = new Interface(marketplaceAbi);
export const SETTLEMENT_CURRENCY = "USDC" as const;
export const SETTLEMENT_DECIMALS = 6 as const;
const erc20Abi = [
  "function allowance(address owner,address spender) view returns (uint256)",
  "function approve(address spender,uint256 amount) returns (bool)",
];

function getContractAddress(): string {
  if (!ENV.CONTRACT_ADDRESS) {
    throw new Error("Missing Expo extra contractAddress.");
  }

  try {
    return getAddress(ENV.CONTRACT_ADDRESS);
  } catch {
    throw new Error(`Invalid contractAddress: ${ENV.CONTRACT_ADDRESS}`);
  }
}

function normalizeListingId(listingId: string): string {
  return /^0x[0-9a-fA-F]{64}$/.test(listingId)
    ? listingId
    : uuidToBytes32(listingId);
}

function formatWholeWithSeparators(value: string): string {
  return value.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function trimTrailingZeros(value: string): string {
  return value
    .replace(/(\.\d*?[1-9])0+$/, "$1")
    .replace(/\.0+$/, "")
    .replace(/\.$/, "");
}

export async function getEvmProvider() {
  const eip1193 = await walletRuntime.getEip1193Provider();
  const provider = new BrowserProvider(
    eip1193 as Parameters<typeof BrowserProvider>[0],
  );
  const network = await provider.getNetwork();

  if (Number(network.chainId) !== ENV.CHAIN_ID) {
    throw new Error(
      `Wrong network. Expected chain ${ENV.CHAIN_ID}, got ${network.chainId.toString()}.`,
    );
  }

  return provider;
}

export async function getConnectedAddress() {
  const provider = await getEvmProvider();
  const signer = await provider.getSigner();
  return signer.getAddress();
}

export async function createItemTx(params: {
  listingId: string;
  title: string;
  description: string;
  seller: string;
  priceAtomic: string;
  datasetUrl: string;
  datasetHash: string;
  signatureUrl: string;
  signatureHash: string;
}) {
  try {
    const provider = await getEvmProvider();
    const signer = await provider.getSigner();
    const signerAddress = await signer.getAddress();

    if (!isSameAddress(signerAddress, params.seller)) {
      throw new Error("Connected wallet does not match the seller address.");
    }

    const contract = new Contract(getContractAddress(), marketplaceAbi, signer);
    const itemId = normalizeListingId(params.listingId);

    await contract.createItem.staticCall(
      itemId,
      params.title,
      params.description,
      params.seller,
      params.priceAtomic,
      params.datasetUrl,
      params.datasetHash,
      params.signatureUrl,
      params.signatureHash,
    );

    const tx = await contract.createItem(
      itemId,
      params.title,
      params.description,
      params.seller,
      params.priceAtomic,
      params.datasetUrl,
      params.datasetHash,
      params.signatureUrl,
      params.signatureHash,
    );
    const receipt = await tx.wait();

    return receipt?.hash ?? tx.hash;
  } catch (error) {
    throw new Error(formatEvmError(error, "create item"));
  }
}

export async function buyItemTx(
  listingId: string,
  priceAtomic: string | bigint,
) {
  try {
    const provider = await getEvmProvider();
    const signer = await provider.getSigner();
    const contract = new Contract(getContractAddress(), marketplaceAbi, signer);
    const feeBps = (await contract.feeBps()) as bigint;
    const normalizedPrice = BigInt(priceAtomic);
    const fee = (normalizedPrice * feeBps) / 10_000n;
    const total = normalizedPrice + fee;

    const tokenAddress = getAddress((await contract.settlementToken()) as string);
    const settlementToken = new Contract(tokenAddress, erc20Abi, signer);
    const buyerAddress = await signer.getAddress();
    const allowance = (await settlementToken.allowance(
      buyerAddress,
      getContractAddress(),
    )) as bigint;

    if (allowance < total) {
      const approvalTx = await settlementToken.approve(getContractAddress(), total);
      await approvalTx.wait();
    }

    const tx = await contract.buyItem(normalizeListingId(listingId));
    const receipt = await tx.wait();

    return receipt?.hash ?? tx.hash;
  } catch (error) {
    throw new Error(formatEvmError(error, "buy item"));
  }
}

export function parseSettlementAmount(
  amount: string,
  decimals: number = SETTLEMENT_DECIMALS,
): string | null {
  const normalized = amount.trim().replace(/,/g, "");
  if (!normalized) {
    return null;
  }

  if (!/^\d+(?:\.\d+)?$/.test(normalized)) {
    return null;
  }

  try {
    return parseUnits(normalized, decimals).toString();
  } catch {
    return null;
  }
}

export function formatSettlementAmount(
  atomicAmount: string | bigint,
  decimals: number = SETTLEMENT_DECIMALS,
): string {
  try {
    const normalized = trimTrailingZeros(formatUnits(atomicAmount, decimals));
    const [whole, fraction] = normalized.split(".");
    const formattedWhole = formatWholeWithSeparators(whole);
    return fraction ? `${formattedWhole}.${fraction}` : formattedWhole;
  } catch {
    return "0";
  }
}

export function isSameAddress(a?: string | null, b?: string | null): boolean {
  if (!a || !b) {
    return false;
  }

  return a.toLowerCase() === b.toLowerCase();
}

export function truncateAddress(address: string, chars = 4): string {
  if (address.length <= chars * 2 + 2) {
    return address;
  }

  return `${address.slice(0, chars + 2)}...${address.slice(-chars)}`;
}

export function formatPurchaseCount(count: number): string {
  return count === 1 ? "1 purchase" : `${count} purchases`;
}

export function listingIdFromItem(item: MarketplaceDataItem): string {
  return item.id;
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
  const revertData = extractErrorData(error);

  if (revertData) {
    try {
      const parsed = errorInterface.parseError(revertData);

      if (parsed?.name) {
        return `Failed to ${action}: ${parsed.name}`;
      }
    } catch {
      // Ignore parse failures and fall back to generic formatting.
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

  return message.trim()
    ? `Failed to ${action}: ${message.trim()}`
    : `Failed to ${action}.`;
}

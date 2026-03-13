import {
  BrowserProvider,
  Contract,
  Interface,
  formatEther,
  getAddress,
  parseEther,
} from "ethers";
import type { Provider as AppKitProvider } from "@reown/appkit-common-react-native";

import { ENV } from "@/constants/env";
import { getAppKit } from "@/src/lib/appkit";
import { uuidToBytes32 } from "@/src/lib/ids";
import { marketplaceAbi } from "@/src/lib/marketplaceAbi";
import type { MarketplaceDataItem } from "@/src/types/contract";

type Eip1193Provider = AppKitProvider;

const errorInterface = new Interface(marketplaceAbi);

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

export function getWalletProvider(): Eip1193Provider {
  const provider = getAppKit()?.getProvider<Eip1193Provider>("eip155");

  if (!provider) {
    throw new Error("No connected WalletConnect provider found.");
  }

  return provider;
}

export async function getEvmProvider() {
  const provider = new BrowserProvider(getWalletProvider());
  const network = await provider.getNetwork();

  if (Number(network.chainId) !== ENV.CHAIN_ID) {
    throw new Error(
      `Wrong network connected. Expected chain ${ENV.CHAIN_ID}, received ${network.chainId.toString()}.`,
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
  priceWei: string;
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
      params.priceWei,
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
      params.priceWei,
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

export async function buyItemTx(listingId: string, priceWei: bigint) {
  try {
    const provider = await getEvmProvider();
    const signer = await provider.getSigner();
    const contract = new Contract(getContractAddress(), marketplaceAbi, signer);
    const feeBps = (await contract.feeBps()) as bigint;
    const fee = (priceWei * feeBps) / 10_000n;
    const total = priceWei + fee;

    const tx = await contract.buyItem(normalizeListingId(listingId), {
      value: total,
    });
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

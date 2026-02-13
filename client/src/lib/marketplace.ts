import {
  BrowserProvider,
  Contract,
  Interface,
  formatEther,
  getAddress,
  parseEther,
} from "ethers";
import { marketplaceAbi } from "@/lib/marketplaceAbi";
import { uuidToBytes32 } from "@/lib/ids";
import type { MarketplaceDataItem } from "@/types/contract";

const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS as
  | string
  | undefined;
const errorInterface = new Interface(marketplaceAbi);

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

export async function getEvmProvider(): Promise<BrowserProvider> {
  if (!window.ethereum) {
    throw new Error("No injected wallet found");
  }
  return new BrowserProvider(window.ethereum);
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
}): Promise<string> {
  try {
    const provider = await getEvmProvider();
    const network = await provider.getNetwork();
    const signer = await provider.getSigner();
    const signerAddress = await signer.getAddress();
    if (!isSameAddress(signerAddress, params.seller)) {
      throw new Error("Connected wallet does not match seller address.");
    }
    const contractAddress = getContractAddress();
    const code = await provider.getCode(contractAddress);
    if (!code || code === "0x") {
      const chainId = network.chainId?.toString?.() ?? String(network.chainId);
      throw new Error(
        `No contract code found at ${contractAddress} on chain ${chainId}. ` +
          "Check MetaMask network and VITE_CONTRACT_ADDRESS deployment target."
      );
    }
    const contract = new Contract(contractAddress, marketplaceAbi, signer);
    const itemId = uuidToBytes32(params.listingId);
    if (!/^0x[0-9a-fA-F]{64}$/.test(params.datasetHash)) {
      throw new Error("Invalid dataset hash format. Expected 0x-prefixed 32-byte hex.");
    }
    if (!/^0x[0-9a-fA-F]{64}$/.test(params.signatureHash)) {
      throw new Error("Invalid signature hash format. Expected 0x-prefixed 32-byte hex.");
    }
    console.info("[createItemTx] submit", {
      chainId: network.chainId?.toString?.() ?? String(network.chainId),
      contract: contractAddress,
      seller: signerAddress,
      itemId,
      priceWei: params.priceWei,
      datasetUrl: params.datasetUrl,
      signatureUrl: params.signatureUrl,
    });
    try {
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
    } catch (error) {
      console.error("[createItemTx] preflight revert", error);
      throw new Error(formatEvmError(error, "create item (preflight)"));
    }
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
  priceWei: bigint,
): Promise<string> {
  try {
    const provider = await getEvmProvider();
    const signer = await provider.getSigner();
    const contract = new Contract(getContractAddress(), marketplaceAbi, signer);
    const feeBps = await contract.feeBps();
    const fee = (priceWei * BigInt(feeBps)) / 10_000n;
    const total = priceWei + fee;
    const tx = await contract.buyItem(listingIdBytes32, { value: total });
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

import { resolveIpfsUrl } from "@/lib/ipfs";

async function sha256Hex(data: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", data);
  const bytes = new Uint8Array(digest);
  return `0x${Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")}`;
}

function normalizeHash(hash: string): string {
  return hash.trim().toLowerCase();
}

async function fetchAndHash(url: string): Promise<string> {
  const resolved = resolveIpfsUrl(url);
  const response = await fetch(resolved);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${resolved} (${response.status})`);
  }
  const data = await response.arrayBuffer();
  return sha256Hex(data);
}

export type IntegrityStatus =
  | "verifying"
  | "verified"
  | "failed"
  | "unavailable";

export async function verifyDatasetIntegrity(input: {
  datasetUrl: string;
  datasetHash: string;
  signatureUrl: string;
  signatureHash: string;
}): Promise<{ status: IntegrityStatus; detail?: string }> {
  if (
    !input.datasetUrl ||
    !input.signatureUrl ||
    !input.datasetHash ||
    !input.signatureHash
  ) {
    return { status: "unavailable", detail: "Missing URL or hash." };
  }

  try {
    const [datasetActual, signatureActual] = await Promise.all([
      fetchAndHash(input.datasetUrl),
      fetchAndHash(input.signatureUrl),
    ]);
    const datasetMatch =
      normalizeHash(datasetActual) === normalizeHash(input.datasetHash);
    const signatureMatch =
      normalizeHash(signatureActual) === normalizeHash(input.signatureHash);
    if (datasetMatch && signatureMatch) {
      return { status: "verified" };
    }
    return {
      status: "failed",
      detail: "Hash mismatch detected for dataset or signature payload.",
    };
  } catch (error) {
    return {
      status: "unavailable",
      detail: error instanceof Error ? error.message : "Integrity check failed",
    };
  }
}

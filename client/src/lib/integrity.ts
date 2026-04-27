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
}): Promise<{ status: IntegrityStatus; detail?: string }> {
  if (!input.datasetUrl || !input.datasetHash) {
    return { status: "unavailable", detail: "Missing URL or hash." };
  }

  try {
    const datasetActual = await fetchAndHash(input.datasetUrl);
    const datasetMatch =
      normalizeHash(datasetActual) === normalizeHash(input.datasetHash);
    if (datasetMatch) {
      return { status: "verified" };
    }
    return {
      status: "failed",
      detail: "Hash mismatch detected for dataset payload.",
    };
  } catch (error) {
    return {
      status: "unavailable",
      detail: error instanceof Error ? error.message : "Integrity check failed",
    };
  }
}

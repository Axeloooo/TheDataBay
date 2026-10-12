import { backend } from "@/lib/backend";
import { decodeBase64, decryptAesGcm, utf8Bytes } from "@/lib/crypto";
import { bytes32ToUuid } from "@/lib/ids";
import { resolveIpfsUrl } from "@/lib/ipfs";

export type DownloadStep = "authorizing" | "decrypting" | "downloading";

/**
 * Release the key for a purchased listing, fetch the encrypted payload,
 * decrypt it and hand the CSV to the browser. Same flow as DatasetDetail.
 */
export async function downloadPurchasedDataset(
  listingId: string,
  datasetUrl: string,
  onStep?: (step: DownloadStep) => void,
): Promise<void> {
  const listingUuid = bytes32ToUuid(listingId);
  onStep?.("authorizing");
  const keyResponse = await backend.requestKeyRelease(listingUuid);
  onStep?.("decrypting");
  const res = await fetch(resolveIpfsUrl(datasetUrl));
  if (!res.ok) {
    throw new Error(`Failed to download dataset (${res.status})`);
  }
  const plaintext = await decryptAesGcm({
    ciphertext: await res.arrayBuffer(),
    key: decodeBase64(keyResponse.key_b64),
    nonce: decodeBase64(keyResponse.nonce_b64),
    aad: utf8Bytes(listingUuid),
  });
  onStep?.("downloading");
  const url = URL.createObjectURL(new Blob([plaintext], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = `${listingUuid}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

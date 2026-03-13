import { ENV } from "@/constants/env";

export function resolveIpfsUrl(url: string): string {
  if (url.startsWith("ipfs://")) {
    const cid = url.slice("ipfs://".length);
    return `${ENV.PINATA_GATEWAY_URL.replace(/\/$/, "")}/ipfs/${cid}`;
  }
  return url;
}

const DEFAULT_GATEWAY = "https://gateway.pinata.cloud";

export function resolveIpfsUrl(url: string): string {
  if (url.startsWith("ipfs://")) {
    const cid = url.slice("ipfs://".length);
    const gateway =
      (import.meta.env.VITE_PINATA_GATEWAY_URL as string | undefined) ||
      DEFAULT_GATEWAY;
    return `${gateway.replace(/\/$/, "")}/ipfs/${cid}`;
  }
  return url;
}

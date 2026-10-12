import { cn } from "@/lib/utils";

export type SupportedChain = "evm" | "solana";

// eslint-disable-next-line react-refresh/only-export-components
export function detectAddressChain(address: string): SupportedChain | null {
  if (/^0x[a-fA-F0-9]{40}$/.test(address)) {
    return "evm";
  }
  if (/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address)) {
    return "solana";
  }
  return null;
}

interface ChainIconProps {
  chain: SupportedChain;
  className?: string;
}

export function ChainIcon({ chain, className }: ChainIconProps) {
  const src = chain === "evm" ? "/eth-logo.svg" : "/sol-logo.svg";

  return (
    <img
      src={src}
      alt=""
      aria-hidden="true"
      className={cn("shrink-0 object-contain", className)}
    />
  );
}

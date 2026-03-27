import { useState, useEffect, useRef } from "react";
import { Loader2, AlertCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useWalletStore } from "@/stores/wallet-store";
import type { WalletConnectorType } from "@/lib/wallet/types";

const RDNS_TO_WALLET: Record<string, { name: string; icon: string }> = {
  "io.metamask":         { name: "MetaMask",        icon: "/metamask-logo.svg" },
  "xyz.rabby":           { name: "Rabby",            icon: "/rabby-logo.svg" },
  "app.phantom":         { name: "Phantom",          icon: "/phantom-logo.svg" },
  "com.brave.wallet":    { name: "Brave Wallet",     icon: "/brave-logo.svg" },
  "com.coinbase.wallet": { name: "Coinbase Wallet",  icon: "/coinbase-logo.svg" },
  "com.trustwallet.app": { name: "Trust Wallet",     icon: "/trust-logo.svg" },
};

type InjectedWalletOption = {
  id: "injected";
  rdns: string;
  name: string;
  icon: string;
  isActive: boolean;
};

type OtherWalletOption = {
  id: Exclude<WalletConnectorType, "injected">;
  name: string;
  icon: string;
  isActive: boolean;
};

type WalletOption = InjectedWalletOption | OtherWalletOption;

function WalletIcon({ src, name }: { src: string; name: string }) {
  return (
    <img
      src={src}
      alt={name}
      className="size-10 object-contain"
      onError={(e) => {
        (e.currentTarget as HTMLImageElement).style.display = "none";
      }}
    />
  );
}

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function WalletConnectModal({ open, onOpenChange }: Props) {
  const { connect, isConnecting, isConnected } = useWalletStore();
  const [selectedWallet, setSelectedWallet] = useState<WalletOption | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [detectedRdns, setDetectedRdns] = useState<Set<string>>(new Set());
  const eip6963ProvidersRef = useRef<Map<string, object>>(new Map());

  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleAnnounce = (event: Event) => {
      const e = event as CustomEvent<{
        info: { name: string; icon: string; rdns: string };
        provider: object;
      }>;
      const { rdns } = e.detail.info;
      if (rdns in RDNS_TO_WALLET) {
        eip6963ProvidersRef.current.set(rdns, e.detail.provider);
        setDetectedRdns((prev) => {
          if (prev.has(rdns)) return prev;
          const next = new Set(prev);
          next.add(rdns);
          return next;
        });
      }
    };

    window.addEventListener("eip6963:announceProvider", handleAnnounce);
    window.dispatchEvent(new Event("eip6963:requestProvider"));

    return () => {
      window.removeEventListener("eip6963:announceProvider", handleAnnounce);
    };
  }, []);

  useEffect(() => {
    if (isConnected && open) {
      onOpenChange(false);
    }
  }, [isConnected, open, onOpenChange]);

  const injectedOptions: InjectedWalletOption[] = Object.entries(RDNS_TO_WALLET)
    .map(([rdns, { name, icon }]) => ({
      id: "injected" as const,
      rdns,
      name,
      icon,
      isActive: detectedRdns.has(rdns),
    }))
    .sort((a, b) => (b.isActive ? 1 : 0) - (a.isActive ? 1 : 0));

  const walletOptions: WalletOption[] = [
    ...injectedOptions,
    { id: "walletconnect", name: "WalletConnect", icon: "/walletconnect-logo.svg", isActive: true },
  ];

  const handleSelect = async (wallet: WalletOption) => {
    if (wallet.id === "injected" && !wallet.isActive) return;

    if (wallet.id === "walletconnect") {
      // Close our modal first — releases Radix scroll lock before WC QR modal opens
      onOpenChange(false);
      await connect("walletconnect");
      return;
    }

    setSelectedWallet(wallet);
    setError(null);
    try {
      const provider = eip6963ProvidersRef.current.get((wallet as InjectedWalletOption).rdns);
      await connect(wallet.id, provider);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Connection failed. Please try again.";
      setError(message);
    }
  };

  const handleReset = () => {
    setSelectedWallet(null);
    setError(null);
  };

  const handleOpenChange = (next: boolean) => {
    if (!isConnecting) {
      if (!next) handleReset();
      onOpenChange(next);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-sm" showCloseButton={!isConnecting}>
        <DialogHeader>
          <DialogTitle className="text-center">
            {isConnecting ? "Connecting…" : "Connect Wallet"}
          </DialogTitle>
        </DialogHeader>

        {/* Loading state */}
        {isConnecting && selectedWallet && !error && (
          <div className="flex flex-col items-center gap-4 py-6">
            <div className="flex size-16 items-center justify-center rounded-2xl border border-border/80 bg-card/80 shadow-sm">
              <WalletIcon src={selectedWallet.icon} name={selectedWallet.name} />
            </div>
            <Loader2 className="size-5 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">
              Connecting to {selectedWallet.name}…
            </p>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="flex flex-col items-center gap-4 py-4">
            <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              <AlertCircle className="size-4 shrink-0" />
              <span>{error}</span>
            </div>
            <Button variant="outline" size="sm" onClick={handleReset}>
              Try Again
            </Button>
          </div>
        )}

        {/* Selection state — icon-only grid */}
        {!isConnecting && !error && (
          <div className="py-2">
            <div className="grid grid-cols-4 gap-3">
              {walletOptions.map((wallet) => {
                const inactive = wallet.id === "injected" && !wallet.isActive;
                return (
                  <button
                    key={wallet.id === "injected" ? `injected-${(wallet as InjectedWalletOption).rdns}` : wallet.id}
                    title={wallet.name}
                    onClick={() => void handleSelect(wallet)}
                    disabled={inactive}
                    className={[
                      "flex aspect-square items-center justify-center rounded-xl border transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      inactive
                        ? "cursor-not-allowed border-border/40 bg-card/20 opacity-40"
                        : "border-border/80 bg-card/60 hover:border-primary/40 hover:bg-accent/50",
                    ].join(" ")}
                  >
                    <WalletIcon src={wallet.icon} name={wallet.name} />
                  </button>
                );
              })}

              {/* Solana placeholder */}
              <button
                disabled
                title="Solana — coming soon"
                className="flex aspect-square cursor-not-allowed items-center justify-center rounded-xl border border-border/40 bg-card/20 opacity-40 focus-visible:outline-none"
              >
                <img
                  src="/sol-logo.svg"
                  alt="Solana"
                  className="size-10 object-contain"
                  onError={(e) => {
                    (e.currentTarget as HTMLImageElement).style.display = "none";
                  }}
                />
              </button>
            </div>

            {detectedRdns.size === 0 && (
              <p className="mt-3 text-center text-xs text-muted-foreground">
                No browser wallets detected. Install a wallet extension or use WalletConnect.
              </p>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

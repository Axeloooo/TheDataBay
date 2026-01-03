import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

type WalletState = {
  address: string | null;
  isConnected: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
};

declare global {
  interface Window {
    ethereum?: {
      request: (args: { method: string; params?: unknown[] }) => Promise<any>;
      on?: (event: string, cb: (...args: any[]) => void) => void;
      removeListener?: (event: string, cb: (...args: any[]) => void) => void;
    };
  }
}

const WalletContext = createContext<WalletState | null>(null);

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [address, setAddress] = useState<string | null>(null);

  const isConnected = !!address;

  const connect = async () => {
    if (!window.ethereum) {
      // You can replace this with a toast/modal
      alert(
        "No injected wallet found. Please install MetaMask (or a compatible wallet)."
      );
      return;
    }
    const accounts: string[] = await window.ethereum.request({
      method: "eth_requestAccounts",
    });
    setAddress(accounts?.[0] ?? null);
  };

  const disconnect = () => {
    // NOTE: Most injected wallets don't support programmatic "disconnect".
    // We just clear app state.
    setAddress(null);
  };

  // Keep state in sync if user switches accounts in wallet UI
  useEffect(() => {
    if (!window.ethereum?.on) return;

    const handleAccountsChanged = (accounts: string[]) => {
      setAddress(accounts?.[0] ?? null);
    };

    const handleChainChanged = () => {
      // Optional: you can reload, or re-init providers/clients here
      // window.location.reload();
    };

    window.ethereum.on("accountsChanged", handleAccountsChanged);
    window.ethereum.on("chainChanged", handleChainChanged);

    return () => {
      window.ethereum?.removeListener?.(
        "accountsChanged",
        handleAccountsChanged
      );
      window.ethereum?.removeListener?.("chainChanged", handleChainChanged);
    };
  }, []);

  const value = useMemo(
    () => ({ address, isConnected, connect, disconnect }),
    [address, isConnected]
  );

  return (
    <WalletContext.Provider value={value}>{children}</WalletContext.Provider>
  );
}

export function useWallet() {
  const ctx = useContext(WalletContext);
  if (!ctx) throw new Error("useWallet must be used within WalletProvider");
  return ctx;
}

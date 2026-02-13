import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  useCallback,
} from "react";

type WalletState = {
  address: string | null;
  isConnected: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
};

const WalletContext = createContext<WalletState | null>(null);

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [address, setAddress] = useState<string | null>(() => {
    const saved = localStorage.getItem("bridgemart_wallet_address");
    return saved || null;
  });

  const isConnected = !!address;

  const connect = useCallback(async () => {
    if (!window.ethereum) {
      // You can replace this with a toast/modal
      alert(
        "No injected wallet found. Please install MetaMask (or a compatible wallet)."
      );
      return;
    }
    try {
      await window.ethereum.request({
        method: "wallet_requestPermissions",
        params: [{ eth_accounts: {} }],
      });
    } catch {
      // Fallback for wallets that do not support permissions API.
    }
    const accounts: string[] = await window.ethereum.request({
      method: "eth_requestAccounts",
    });
    const next = accounts?.[0] ?? null;
    setAddress(next);
    if (next) {
      localStorage.setItem("bridgemart_wallet_address", next);
    }
  }, []);

  const disconnect = useCallback(() => {
    // NOTE: Most injected wallets don't support programmatic "disconnect".
    // We just clear app state.
    setAddress(null);
    localStorage.removeItem("bridgemart_wallet_address");
  }, []);

  // Keep state in sync if user switches accounts in wallet UI
  useEffect(() => {
    if (!window.ethereum?.on) return;

    const handleAccountsChanged = (accounts: string[]) => {
      if (!accounts?.length) {
        return;
      }
      setAddress(accounts[0]);
      localStorage.setItem("bridgemart_wallet_address", accounts[0]);
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
    [address, isConnected, connect, disconnect]
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

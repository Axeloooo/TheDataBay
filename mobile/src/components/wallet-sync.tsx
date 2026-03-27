import { useEffect } from "react";

import { useWalletStore } from "@/src/stores/wallet-store";

export function WalletSync() {
  const subscribeToRuntime = useWalletStore((s) => s.subscribeToRuntime);

  useEffect(() => {
    const unsubscribe = subscribeToRuntime();
    return () => unsubscribe();
  }, [subscribeToRuntime]);

  return null;
}

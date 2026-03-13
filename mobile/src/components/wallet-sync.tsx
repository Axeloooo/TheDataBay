import { useEffect } from "react";
import {
  useAccount,
  useAppKitState,
  useWalletInfo,
} from "@reown/appkit-react-native";

import { useWalletStore } from "@/src/stores/wallet-store";

export function WalletSync() {
  const { address, chain, chainId, isConnected } = useAccount();
  const { isLoading } = useAppKitState();
  const { walletInfo } = useWalletInfo();
  const syncConnection = useWalletStore((state) => state.syncConnection);

  useEffect(() => {
    syncConnection({
      address: address ?? null,
      chainId: chainId ?? null,
      chainName: chain?.name ?? null,
      walletName: walletInfo?.name ?? null,
      walletIcon: walletInfo?.icon ?? walletInfo?.icons?.[0] ?? null,
      isConnected,
      isConnecting: isLoading,
    });
  }, [
    address,
    chain?.name,
    chainId,
    isConnected,
    isLoading,
    syncConnection,
    walletInfo?.icon,
    walletInfo?.icons,
    walletInfo?.name,
  ]);

  return null;
}

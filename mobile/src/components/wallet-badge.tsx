import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";
import { truncateAddress } from "@/src/lib/marketplace";
import { AppButton } from "@/components/ui/app-button";
import { StatusPill } from "@/components/ui/status-pill";

type Props = {
  address: string | null;
  isConnected: boolean;
  isConnecting: boolean;
  walletName?: string | null;
  chainName?: string | null;
  onConnect: () => void;
  onDisconnect: () => void;
};

export default function WalletBadge({
  address,
  isConnected,
  isConnecting,
  walletName,
  chainName,
  onConnect,
  onDisconnect,
}: Props) {
  const palette = useAppTheme();

  if (isConnected && address) {
    return (
      <View style={styles.connectedShell}>
        <View style={styles.connectedHeader}>
          <StatusPill label={chainName ?? "Connected"} tone="success" />
          <Text style={[styles.walletLabel, { color: palette.subtleText }]}>
            {walletName ?? "WalletConnect"}
          </Text>
        </View>
        <Text style={[styles.address, { color: palette.text }]}>
          {truncateAddress(address, 6)}
        </Text>
        <AppButton
          label="Disconnect"
          onPress={onDisconnect}
          variant="secondary"
        />
      </View>
    );
  }

  return (
    <View style={styles.disconnectedShell}>
      <Text style={[styles.walletHeading, { color: palette.text }]}>
        WalletConnect v2
      </Text>
      <Text style={[styles.walletHint, { color: palette.subtleText }]}>
        Connect a wallet to buy datasets, resume purchases, and create new
        listings from your phone.
      </Text>
      <AppButton
        label="Connect Wallet"
        onPress={onConnect}
        loading={isConnecting}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  connectedShell: {
    gap: AppTheme.spacing.md,
  },
  connectedHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: AppTheme.spacing.sm,
  },
  walletLabel: {
    fontSize: 12,
    fontWeight: "700",
  },
  address: {
    fontSize: 24,
    fontWeight: "800",
    letterSpacing: -0.5,
  },
  disconnectedShell: {
    gap: AppTheme.spacing.md,
  },
  walletHeading: {
    fontSize: 22,
    fontWeight: "800",
  },
  walletHint: {
    fontSize: 14,
    lineHeight: 21,
  },
});

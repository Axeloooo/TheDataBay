import React, { useState } from "react";
import {
  Linking,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";
import { walletRuntime } from "@/src/lib/wallet/runtime";
import { useWalletStore } from "@/src/stores/wallet-store";

type WalletOption = {
  id: string;
  name: string;
  scheme: string;
};

const WALLETS: WalletOption[] = [
  { id: "metamask", name: "MetaMask", scheme: "metamask://wc?uri=" },
  { id: "trust", name: "Trust Wallet", scheme: "trust://wc?uri=" },
  { id: "rainbow", name: "Rainbow", scheme: "rainbow://wc?uri=" },
  { id: "coinbase", name: "Coinbase Wallet", scheme: "cbwallet://wc?uri=" },
];

export function WalletPicker() {
  const palette = useAppTheme();
  const pendingWcUri = useWalletStore((s) => s.pendingWcUri);
  const clearPendingUri = useWalletStore((s) => s.clearPendingUri);
  const failMutation = useWalletStore((s) => s.failMutation);
  const [awaitingWallet, setAwaitingWallet] = useState<string | null>(null);

  const isVisible = pendingWcUri != null;

  async function handleWalletPress(wallet: WalletOption) {
    if (!pendingWcUri || awaitingWallet) return;

    setAwaitingWallet(wallet.id);

    try {
      await Linking.openURL(wallet.scheme + encodeURIComponent(pendingWcUri));
      await walletRuntime.awaitConnection();
      clearPendingUri();
    } catch {
      clearPendingUri();
      failMutation("Connection timed out or rejected.");
    } finally {
      setAwaitingWallet(null);
    }
  }

  async function handleCancel() {
    try {
      await walletRuntime.disconnect();
    } catch {
      // Ignore cancel errors
    } finally {
      clearPendingUri();
      setAwaitingWallet(null);
    }
  }

  return (
    <Modal
      visible={isVisible}
      transparent
      animationType="slide"
      onRequestClose={() => void handleCancel()}
    >
      <View style={styles.overlay}>
        <View
          style={[
            styles.sheet,
            { backgroundColor: palette.card, borderColor: palette.border },
          ]}
        >
          <Text style={[styles.heading, { color: palette.text }]}>
            Choose a Wallet
          </Text>
          <Text style={[styles.subheading, { color: palette.subtleText }]}>
            Select a wallet app to approve the connection request.
          </Text>

          <View style={styles.walletList}>
            {WALLETS.map((wallet) => {
              const isLoading = awaitingWallet === wallet.id;
              return (
                <Pressable
                  key={wallet.id}
                  onPress={() => void handleWalletPress(wallet)}
                  disabled={awaitingWallet != null}
                  style={({ pressed }) => [
                    styles.walletRow,
                    {
                      backgroundColor: pressed
                        ? palette.cardMuted
                        : palette.card,
                      borderColor: palette.border,
                    },
                  ]}
                >
                  <Text style={[styles.walletName, { color: palette.text }]}>
                    {wallet.name}
                  </Text>
                  {isLoading ? (
                    <Text
                      style={[styles.waitingLabel, { color: palette.subtleText }]}
                    >
                      Waiting…
                    </Text>
                  ) : null}
                </Pressable>
              );
            })}
          </View>

          {pendingWcUri ? (
            <View
              style={[
                styles.rawUriContainer,
                { backgroundColor: palette.cardMuted, borderColor: palette.border },
              ]}
            >
              <Text style={[styles.rawUriLabel, { color: palette.subtleText }]}>
                Or copy the WalletConnect URI:
              </Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                <Text
                  selectable
                  style={[styles.rawUri, { color: palette.text }]}
                >
                  {pendingWcUri}
                </Text>
              </ScrollView>
            </View>
          ) : null}

          <Pressable
            onPress={() => void handleCancel()}
            style={({ pressed }) => [
              styles.cancelButton,
              {
                backgroundColor: pressed ? palette.cardMuted : "transparent",
                borderColor: palette.border,
              },
            ]}
          >
            <Text style={[styles.cancelLabel, { color: palette.subtleText }]}>
              Cancel
            </Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(0,0,0,0.5)",
  },
  sheet: {
    borderTopLeftRadius: AppTheme.radius.lg,
    borderTopRightRadius: AppTheme.radius.lg,
    borderTopWidth: 1,
    paddingHorizontal: AppTheme.spacing.md,
    paddingTop: AppTheme.spacing.lg,
    paddingBottom: AppTheme.spacing.xxl,
    gap: AppTheme.spacing.md,
  },
  heading: {
    fontSize: 20,
    fontWeight: "800",
  },
  subheading: {
    fontSize: 14,
    lineHeight: 20,
  },
  walletList: {
    gap: AppTheme.spacing.xs,
  },
  walletRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: AppTheme.spacing.md,
    paddingVertical: AppTheme.spacing.md,
    borderRadius: AppTheme.radius.md,
    borderWidth: 1,
  },
  walletName: {
    fontSize: 16,
    fontWeight: "700",
  },
  waitingLabel: {
    fontSize: 13,
    fontWeight: "600",
  },
  rawUriContainer: {
    borderRadius: AppTheme.radius.md,
    borderWidth: 1,
    padding: AppTheme.spacing.sm,
    gap: AppTheme.spacing.xs,
  },
  rawUriLabel: {
    fontSize: 12,
    fontWeight: "600",
  },
  rawUri: {
    fontSize: 11,
    fontFamily: "monospace",
  },
  cancelButton: {
    alignItems: "center",
    paddingVertical: AppTheme.spacing.md,
    borderRadius: AppTheme.radius.md,
    borderWidth: 1,
  },
  cancelLabel: {
    fontSize: 16,
    fontWeight: "700",
  },
});

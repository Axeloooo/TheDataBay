import React, { useEffect } from "react";
import { ScrollView, StyleSheet, Text, View, Pressable } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";

import ErrorPanel from "@/components/error-panel";
import PurchaseRow from "@/components/purchase-row";
import WalletBadge from "@/components/wallet-badge";
import { AppButton } from "@/components/ui/app-button";
import { SurfaceCard } from "@/components/ui/surface-card";
import { StatusPill } from "@/components/ui/status-pill";
import { AppTheme } from "@/constants/theme";
import { ENV } from "@/constants/env";
import { useAppTheme } from "@/hooks/use-app-theme";
import { useCurrencyStore } from "@/src/stores/currency-store";
import { useMarketplaceStore } from "@/src/stores/marketplace-store";
import { useWalletStore } from "@/src/stores/wallet-store";
import type { DisplayCurrency } from "@/src/lib/fx";

const CURRENCIES: DisplayCurrency[] = [
  "ETH",
  "USD",
  "CAD",
  "EUR",
  "USDC",
  "SOL",
];

export default function WalletScreen() {
  const palette = useAppTheme();
  const {
    address,
    chainName,
    walletName,
    isConnected,
    isConnecting,
    transactionError,
    configError,
    openConnectModal,
    disconnectWallet,
  } = useWalletStore();
  const { preferredCurrency, setPreferredCurrency } = useCurrencyStore();
  const {
    purchases,
    purchasesLoading,
    purchasesError,
    fetchPurchases,
    clearPurchases,
  } = useMarketplaceStore();

  useEffect(() => {
    if (isConnected && address) {
      void fetchPurchases(address, true);
    } else {
      clearPurchases();
    }
  }, [address, clearPurchases, fetchPurchases, isConnected]);

  return (
    <SafeAreaView
      edges={["top"]}
      style={[styles.container, { backgroundColor: palette.background }]}
    >
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.hero}>
          <Text style={[styles.eyebrow, { color: palette.subtleText }]}>
            Wallet hub
          </Text>
          <Text style={[styles.title, { color: palette.text }]}>
            Connection, purchases, and app controls
          </Text>
        </View>

        <SurfaceCard style={styles.card}>
          <WalletBadge
            address={address}
            isConnected={isConnected}
            isConnecting={isConnecting}
            walletName={walletName}
            chainName={chainName}
            onConnect={() => void openConnectModal()}
            onDisconnect={() => void disconnectWallet()}
          />
          {configError ? <ErrorPanel message={configError} /> : null}
          {transactionError && !configError ? (
            <ErrorPanel message={transactionError} />
          ) : null}
        </SurfaceCard>

        <SurfaceCard style={styles.card}>
          <View style={styles.rowBetween}>
            <Text style={[styles.sectionTitle, { color: palette.text }]}>
              Display currency
            </Text>
            <StatusPill label={preferredCurrency} tone="info" />
          </View>
          <View style={styles.chipWrap}>
            {CURRENCIES.map((currency) => {
              const active = currency === preferredCurrency;
              return (
                <Pressable
                  key={currency}
                  onPress={() => setPreferredCurrency(currency)}
                  style={[
                    styles.chip,
                    {
                      backgroundColor: active
                        ? palette.tint
                        : palette.cardMuted,
                      borderColor: active ? palette.tint : palette.border,
                    },
                  ]}
                >
                  <Text
                    style={[
                      styles.chipLabel,
                      { color: active ? "#ffffff" : palette.text },
                    ]}
                  >
                    {currency}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </SurfaceCard>

        <SurfaceCard style={styles.card}>
          <View style={styles.rowBetween}>
            <Text style={[styles.sectionTitle, { color: palette.text }]}>
              Purchased datasets
            </Text>
            <Text style={[styles.sectionHint, { color: palette.subtleText }]}>
              {purchasesLoading ? "Loading…" : `${purchases.length} items`}
            </Text>
          </View>
          {purchasesError ? (
            <ErrorPanel message={purchasesError} />
          ) : purchases.length === 0 ? (
            <Text style={[styles.sectionHint, { color: palette.subtleText }]}>
              Buy a dataset from the marketplace and it will appear here for
              quick access.
            </Text>
          ) : (
            <View style={styles.purchaseList}>
              {purchases.map((item) => (
                <PurchaseRow
                  key={item.id}
                  item={item}
                  onPress={() => router.push(`/dataset/${item.id}`)}
                />
              ))}
            </View>
          )}
        </SurfaceCard>

        <SurfaceCard style={styles.card}>
          <Text style={[styles.sectionTitle, { color: palette.text }]}>
            Runtime config
          </Text>
          <Text style={[styles.sectionHint, { color: palette.subtleText }]}>
            API: {ENV.API_URL}
          </Text>
          <Text style={[styles.sectionHint, { color: palette.subtleText }]}>
            Chain ID: {String(ENV.CHAIN_ID)}
          </Text>
          <Text style={[styles.sectionHint, { color: palette.subtleText }]}>
            Contract: {ENV.CONTRACT_ADDRESS || "Not configured"}
          </Text>
          {!isConnected ? (
            <AppButton
              label="Open WalletConnect"
              onPress={() => void openConnectModal()}
            />
          ) : null}
        </SurfaceCard>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    paddingHorizontal: AppTheme.spacing.md,
    paddingTop: AppTheme.spacing.md,
    paddingBottom: AppTheme.spacing.xxl,
    gap: AppTheme.spacing.md,
  },
  hero: {
    gap: AppTheme.spacing.xs,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  title: {
    fontSize: 28,
    fontWeight: "800",
    lineHeight: 34,
  },
  card: {
    gap: AppTheme.spacing.md,
  },
  rowBetween: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: AppTheme.spacing.md,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "800",
  },
  sectionHint: {
    fontSize: 13,
    lineHeight: 20,
  },
  chipWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: AppTheme.spacing.xs,
  },
  chip: {
    borderWidth: 1,
    borderRadius: AppTheme.radius.pill,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  chipLabel: {
    fontSize: 13,
    fontWeight: "700",
  },
  purchaseList: {
    gap: AppTheme.spacing.sm,
  },
});

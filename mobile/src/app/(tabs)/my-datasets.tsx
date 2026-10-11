import React, { useCallback, useEffect } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router, useFocusEffect } from "expo-router";

import ErrorPanel from "@/components/error-panel";
import { AppButton } from "@/components/ui/app-button";
import { SurfaceCard } from "@/components/ui/surface-card";
import { StatusPill } from "@/components/ui/status-pill";
import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";
import { formatSettlementAmount } from "@/src/lib/marketplace";
import { useMeStore } from "@/src/stores/me-store";
import { useWalletStore } from "@/src/stores/wallet-store";

export default function MyDatasetsScreen() {
  const palette = useAppTheme();
  const { address, isConnected } = useWalletStore();
  const { purchases, purchasesLoaded, purchasesError } =
    useMeStore();
  const fetchPurchases = useMeStore((s) => s.fetchPurchases);
  const clear = useMeStore((s) => s.clear);

  // A different wallet (or a disconnect) must never see the previous wallet's rows.
  useEffect(() => {
    clear();
  }, [address, isConnected, clear]);

  // Tabs stay mounted, so refetch every time the screen gains focus.
  useFocusEffect(
    useCallback(() => {
      if (isConnected && address) {
        void fetchPurchases();
      }
    }, [address, isConnected, fetchPurchases]),
  );

  return (
    <SafeAreaView
      edges={["top"]}
      style={[styles.container, { backgroundColor: palette.background }]}
    >
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={[styles.title, { color: palette.text }]}>My datasets</Text>
        <Text style={[styles.hint, { color: palette.subtleText }]}>
          Datasets you have purchased. Open one to download it again.
        </Text>

        {!isConnected ? (
          <Text style={[styles.hint, { color: palette.subtleText }]}>
            Connect your wallet to see your datasets.
          </Text>
        ) : purchasesError ? (
          <ErrorPanel
            title="Could not load your datasets"
            message={purchasesError}
            onRetry={() => void fetchPurchases()}
          />
        ) : !purchasesLoaded ? (
          <Text style={[styles.hint, { color: palette.subtleText }]}>
            Loading…
          </Text>
        ) : purchases.length === 0 ? (
          <SurfaceCard style={styles.card}>
            <Text style={[styles.rowTitle, { color: palette.text }]}>
              You haven&apos;t bought any datasets yet.
            </Text>
            <AppButton
              label="Browse datasets"
              onPress={() => router.push("/")}
            />
          </SurfaceCard>
        ) : (
          purchases.map((item) => (
            <SurfaceCard key={item.listing_id} style={styles.card}>
              <View style={styles.rowBetween}>
                <Text
                  style={[styles.rowTitle, { color: palette.text }]}
                  numberOfLines={1}
                >
                  {item.title}
                </Text>
                <StatusPill
                  label={`${formatSettlementAmount(item.price_paid, item.token_decimals)} ${item.token_symbol}`}
                  tone="info"
                />
              </View>
              <Text style={[styles.hint, { color: palette.subtleText }]}>
                {item.description}
              </Text>
              <AppButton
                label="Open & download"
                onPress={() => router.push(`/dataset/${item.listing_id}`)}
              />
            </SurfaceCard>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: {
    paddingHorizontal: AppTheme.spacing.md,
    paddingTop: AppTheme.spacing.md,
    paddingBottom: AppTheme.spacing.xxl,
    gap: AppTheme.spacing.md,
  },
  title: { fontSize: 28, fontWeight: "800", lineHeight: 34 },
  hint: { fontSize: 13, lineHeight: 20 },
  card: { gap: AppTheme.spacing.sm },
  rowBetween: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: AppTheme.spacing.md,
  },
  rowTitle: { fontSize: 16, fontWeight: "800", flexShrink: 1 },
});

import React, { useEffect } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";

import ErrorPanel from "@/components/error-panel";
import { AppButton } from "@/components/ui/app-button";
import { SurfaceCard } from "@/components/ui/surface-card";
import { StatusPill } from "@/components/ui/status-pill";
import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";
import { formatSettlementAmount } from "@/src/lib/marketplace";
import { useMeStore } from "@/src/stores/me-store";
import { useWalletStore } from "@/src/stores/wallet-store";

export default function SellerScreen() {
  const palette = useAppTheme();
  const { address, isConnected } = useWalletStore();
  const { listings, listingsLoading, listingsLoaded, listingsError } =
    useMeStore();
  const fetchListings = useMeStore((s) => s.fetchListings);
  const clear = useMeStore((s) => s.clear);

  useEffect(() => {
    if (isConnected && address) {
      void fetchListings();
    } else {
      clear();
    }
  }, [address, isConnected, fetchListings, clear]);

  return (
    <SafeAreaView
      edges={["top"]}
      style={[styles.container, { backgroundColor: palette.background }]}
    >
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={[styles.title, { color: palette.text }]}>
          Seller dashboard
        </Text>
        <Text style={[styles.hint, { color: palette.subtleText }]}>
          Your listings, sales and earnings per payment token.
        </Text>

        {!isConnected ? (
          <Text style={[styles.hint, { color: palette.subtleText }]}>
            Connect your wallet to see your listings.
          </Text>
        ) : listingsError ? (
          <ErrorPanel
            title="Could not load your listings"
            message={listingsError}
            onRetry={() => void fetchListings()}
          />
        ) : listingsLoading && !listingsLoaded ? (
          <Text style={[styles.hint, { color: palette.subtleText }]}>
            Loading…
          </Text>
        ) : listings.length === 0 ? (
          <SurfaceCard style={styles.card}>
            <Text style={[styles.rowTitle, { color: palette.text }]}>
              You haven&apos;t listed any datasets yet.
            </Text>
            <AppButton
              label="List a dataset"
              onPress={() => router.push("/upload")}
            />
          </SurfaceCard>
        ) : (
          listings.map((item) => (
            <SurfaceCard key={item.listing_id} style={styles.card}>
              <View style={styles.rowBetween}>
                <Text
                  style={[styles.rowTitle, { color: palette.text }]}
                  numberOfLines={1}
                >
                  {item.title}
                </Text>
                <StatusPill
                  label={`${formatSettlementAmount(item.price, item.token_decimals)} ${item.token_symbol}`}
                  tone="info"
                />
              </View>
              <Text style={[styles.hint, { color: palette.subtleText }]}>
                {item.sales_count} {item.sales_count === 1 ? "sale" : "sales"}
                {Object.values(item.earnings_by_token).map(
                  (amount) =>
                    ` · ${formatSettlementAmount(amount, item.token_decimals)} ${item.token_symbol}`,
                )}
                {item.source === "contract"
                  ? " · earnings unavailable until the indexer is synced"
                  : ""}
              </Text>
              <Text style={[styles.hint, { color: palette.subtleText }]}>
                {item.price_editable
                  ? "Price edits need a wallet-signed transaction, which is not available yet."
                  : "Price can't change after the first sale."}
              </Text>
              <AppButton label="Edit price" disabled onPress={() => undefined} />
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

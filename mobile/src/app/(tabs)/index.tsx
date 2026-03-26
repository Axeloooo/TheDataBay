import React, { useCallback, useEffect, useMemo, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";

import DatasetCard from "@/components/dataset-card";
import ErrorPanel from "@/components/error-panel";
import PurchaseRow from "@/components/purchase-row";
import SkeletonCard from "@/components/skeleton-card";
import { SurfaceCard } from "@/components/ui/surface-card";
import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";
import { useMarketplaceStore } from "@/src/stores/marketplace-store";
import { useWalletStore } from "@/src/stores/wallet-store";

function HeroSection({
  listingCount,
  purchaseCount,
}: {
  listingCount: number;
  purchaseCount: number;
}) {
  const palette = useAppTheme();
  const stats = useMemo(
    () => [
      { label: "Visible listings", value: String(listingCount) },
      { label: "Purchased", value: String(purchaseCount) },
      { label: "Settlement", value: "USDC" },
    ],
    [listingCount, purchaseCount],
  );

  return (
    <View
      style={[
        styles.hero,
        {
          backgroundColor: palette.heroStart,
          borderColor: `${palette.heroEnd}70`,
        },
      ]}
    >
      <View
        style={[styles.heroGlow, { backgroundColor: `${palette.tint}28` }]}
      />
      <Text style={styles.heroEyebrow}>Semantic data marketplace</Text>
      <Text style={styles.heroTitle}>
        Discover verifiable datasets and unlock them with on-chain access.
      </Text>
      <Text style={styles.heroSubtitle}>
        BridgeMart combines encrypted IPFS delivery, semantic search, and
        contract-based access for mobile-native data commerce.
      </Text>

      <View style={styles.statGrid}>
        {stats.map((stat) => (
          <View
            key={stat.label}
            style={[
              styles.statCard,
              { backgroundColor: "rgba(255,255,255,0.08)" },
            ]}
          >
            <Text style={styles.statLabel}>{stat.label}</Text>
            <Text style={styles.statValue}>{stat.value}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

export default function HomeScreen() {
  const palette = useAppTheme();
  const {
    items,
    purchases,
    loading,
    purchasesLoading,
    error,
    purchasesError,
    fetchItems,
    fetchPurchases,
    clearPurchases,
  } = useMarketplaceStore();
  const { address, isConnected } = useWalletStore();
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    void fetchItems();
  }, [fetchItems]);

  useEffect(() => {
    if (isConnected && address) {
      void fetchPurchases(address);
    } else {
      clearPurchases();
    }
  }, [address, clearPurchases, fetchPurchases, isConnected]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchItems(true);
    if (address) {
      await fetchPurchases(address, true);
    }
    setRefreshing(false);
  }, [address, fetchItems, fetchPurchases]);

  const header = (
    <View style={styles.header}>
      <HeroSection
        listingCount={items.length}
        purchaseCount={purchases.length}
      />

      {isConnected ? (
        <View style={styles.section}>
          <View style={styles.sectionHeading}>
            <Text
              style={[styles.sectionEyebrow, { color: palette.subtleText }]}
            >
              My purchases
            </Text>
            <Text style={[styles.sectionCount, { color: palette.subtleText }]}>
              {purchasesLoading ? "Loading…" : `${purchases.length} items`}
            </Text>
          </View>
          {purchasesError ? (
            <ErrorPanel message={purchasesError} />
          ) : purchases.length === 0 && !purchasesLoading ? (
            <SurfaceCard muted>
              <Text style={[styles.emptyCopy, { color: palette.subtleText }]}>
                Purchased datasets will appear here once this wallet completes a
                buy transaction.
              </Text>
            </SurfaceCard>
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
        </View>
      ) : null}

      <View style={styles.sectionHeading}>
        <Text style={[styles.sectionEyebrow, { color: palette.subtleText }]}>
          Marketplace feed
        </Text>
        <Text style={[styles.sectionTitle, { color: palette.text }]}>
          Live dataset listings
        </Text>
      </View>
    </View>
  );

  if (loading && items.length === 0) {
    return (
      <SafeAreaView
        edges={["top"]}
        style={[styles.container, { backgroundColor: palette.background }]}
      >
        <FlatList
          data={Array.from({ length: 4 })}
          keyExtractor={(_, index) => `loading-${index}`}
          contentContainerStyle={styles.content}
          ListHeaderComponent={header}
          renderItem={() => <SkeletonCard />}
        />
      </SafeAreaView>
    );
  }

  if (error && items.length === 0) {
    return (
      <SafeAreaView
        edges={["top"]}
        style={[styles.container, { backgroundColor: palette.background }]}
      >
        <View style={styles.content}>
          {header}
          <ErrorPanel message={error} onRetry={() => void fetchItems(true)} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView
      edges={["top"]}
      style={[styles.container, { backgroundColor: palette.background }]}
    >
      <FlatList
        data={items}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <DatasetCard
            item={item}
            onPress={() => router.push(`/dataset/${item.id}`)}
          />
        )}
        contentContainerStyle={styles.content}
        ListHeaderComponent={header}
        ListEmptyComponent={
          <SurfaceCard muted>
            <Text style={[styles.emptyCopy, { color: palette.subtleText }]}>
              No datasets are visible yet. Pull to refresh after seeding the
              marketplace.
            </Text>
          </SurfaceCard>
        }
        ItemSeparatorComponent={() => (
          <View style={{ height: AppTheme.spacing.md }} />
        )}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={palette.tint}
          />
        }
        showsVerticalScrollIndicator={false}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    paddingHorizontal: AppTheme.spacing.md,
    paddingBottom: AppTheme.spacing.xxl,
    gap: AppTheme.spacing.md,
  },
  header: {
    gap: AppTheme.spacing.xl,
    paddingVertical: AppTheme.spacing.md,
  },
  hero: {
    overflow: "hidden",
    borderWidth: 1,
    borderRadius: AppTheme.radius.xl,
    padding: AppTheme.spacing.xl,
    gap: AppTheme.spacing.md,
  },
  heroGlow: {
    position: "absolute",
    width: 240,
    height: 240,
    borderRadius: 240,
    right: -80,
    top: -70,
  },
  heroEyebrow: {
    color: "#c7dafb",
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  heroTitle: {
    color: "#ffffff",
    fontSize: 30,
    fontWeight: "800",
    lineHeight: 36,
    maxWidth: "90%",
  },
  heroSubtitle: {
    color: "#dbe7ff",
    fontSize: 15,
    lineHeight: 22,
    maxWidth: "92%",
  },
  statGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: AppTheme.spacing.sm,
  },
  statCard: {
    minWidth: "31%",
    flex: 1,
    borderRadius: AppTheme.radius.md,
    padding: AppTheme.spacing.md,
    gap: 6,
  },
  statLabel: {
    color: "#c7dafb",
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  statValue: {
    color: "#ffffff",
    fontSize: 23,
    fontWeight: "800",
  },
  section: {
    gap: AppTheme.spacing.md,
  },
  sectionHeading: {
    gap: 4,
  },
  sectionEyebrow: {
    fontSize: 11,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  sectionTitle: {
    fontSize: 24,
    fontWeight: "800",
  },
  sectionCount: {
    fontSize: 12,
    fontWeight: "600",
  },
  purchaseList: {
    gap: AppTheme.spacing.sm,
  },
  emptyCopy: {
    fontSize: 14,
    lineHeight: 21,
  },
});

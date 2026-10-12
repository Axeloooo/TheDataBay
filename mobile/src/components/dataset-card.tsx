import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";
import {
  formatCurrencyAmount,
  convertSettlementToCurrency,
} from "@/src/lib/fx";
import {
  formatSettlementAmount,
  formatPurchaseCount,
  truncateAddress,
} from "@/src/lib/marketplace";
import { useCurrencyStore } from "@/src/stores/currency-store";
import type { MarketplaceDataItem } from "@/src/types/contract";

type Props = {
  item: MarketplaceDataItem;
  onPress?: () => void;
};

export default function DatasetCard({ item, onPress }: Props) {
  const palette = useAppTheme();
  const displayCurrency = useCurrencyStore((state) => state.displayCurrency);
  const rates = useCurrencyStore((state) => state.rates);
  const settlementAmount = formatSettlementAmount(
    item.price_atomic,
    item.settlement_decimals,
  );
  const isFree = BigInt(item.price_atomic) === 0n;
  const converted =
    !isFree && displayCurrency !== item.settlement_currency
      ? convertSettlementToCurrency(
          item.price_atomic,
          item.settlement_decimals,
          displayCurrency,
          rates,
        )
      : null;

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      style={({ pressed }) => [
        styles.card,
        AppTheme.shadow.card,
        {
          backgroundColor: palette.card,
          borderColor: palette.border,
          opacity: pressed ? 0.94 : 1,
          transform: [{ scale: pressed ? 0.99 : 1 }],
        },
      ]}
    >
      <View style={styles.header}>
        <View style={styles.titleBlock}>
          <Text style={[styles.eyebrow, { color: palette.subtleText }]}>
            Dataset listing
          </Text>
          <Text
            style={[styles.title, { color: palette.text }]}
            numberOfLines={2}
          >
            {item.title}
          </Text>
        </View>
        <View
          style={[styles.priceBadge, { backgroundColor: `${palette.tint}15` }]}
        >
          <Text style={[styles.priceText, { color: palette.tint }]}>
            {isFree
              ? "Free"
              : `${settlementAmount} ${item.settlement_currency}`}
          </Text>
        </View>
      </View>

      <Text
        style={[styles.description, { color: palette.subtleText }]}
        numberOfLines={3}
      >
        {item.description}
      </Text>

      <View style={[styles.divider, { backgroundColor: palette.border }]} />

      <View style={styles.footer}>
        <View>
          <Text style={[styles.metaLabel, { color: palette.subtleText }]}>
            Demand
          </Text>
          <Text style={[styles.metaValue, { color: palette.text }]}>
            {formatPurchaseCount(item.purchase_count)}
          </Text>
        </View>
        <View style={styles.metaRight}>
          {converted !== null && (
            <Text style={[styles.fxText, { color: palette.subtleText }]}>
              ~ {formatCurrencyAmount(converted, displayCurrency)}
            </Text>
          )}
          <Text style={[styles.seller, { color: palette.text }]}>
            {truncateAddress(item.seller)}
          </Text>
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: AppTheme.radius.lg,
    padding: AppTheme.spacing.lg,
    gap: AppTheme.spacing.md,
  },
  header: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: AppTheme.spacing.md,
  },
  titleBlock: {
    flex: 1,
    gap: 6,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.9,
  },
  title: {
    fontSize: 19,
    fontWeight: "800",
    lineHeight: 24,
  },
  priceBadge: {
    borderRadius: AppTheme.radius.pill,
    paddingHorizontal: AppTheme.spacing.md,
    paddingVertical: AppTheme.spacing.xs,
  },
  priceText: {
    fontSize: 12,
    fontWeight: "800",
  },
  description: {
    fontSize: 15,
    lineHeight: 22,
  },
  divider: {
    height: 1,
  },
  footer: {
    flexDirection: "row",
    alignItems: "flex-end",
    justifyContent: "space-between",
    gap: AppTheme.spacing.md,
  },
  metaLabel: {
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.8,
    marginBottom: 4,
  },
  metaValue: {
    fontSize: 14,
    fontWeight: "700",
  },
  metaRight: {
    alignItems: "flex-end",
    gap: 4,
  },
  fxText: {
    fontSize: 12,
    fontWeight: "600",
  },
  seller: {
    fontSize: 13,
    fontWeight: "700",
  },
});

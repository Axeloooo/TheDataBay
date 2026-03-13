import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";
import { truncateAddress, weiToEth } from "@/src/lib/marketplace";
import type { MarketplaceDataItem } from "@/src/types/contract";

type Props = {
  item: MarketplaceDataItem;
  onPress?: () => void;
};

export default function PurchaseRow({ item, onPress }: Props) {
  const palette = useAppTheme();
  const ethPrice = Number.parseFloat(weiToEth(item.price));

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.row,
        {
          backgroundColor: palette.card,
          borderColor: palette.border,
          opacity: pressed ? 0.92 : 1,
        },
      ]}
    >
      <View
        style={[styles.iconContainer, { backgroundColor: `${palette.tint}15` }]}
      >
        <Text style={styles.icon}>⛁</Text>
      </View>
      <View style={styles.content}>
        <Text style={[styles.title, { color: palette.text }]} numberOfLines={1}>
          {item.title}
        </Text>
        <Text style={[styles.meta, { color: palette.subtleText }]}>
          {ethPrice.toLocaleString("en-US", { maximumFractionDigits: 4 })} ETH
        </Text>
      </View>
      <View style={styles.trailing}>
        <Text style={[styles.seller, { color: palette.subtleText }]}>
          {truncateAddress(item.seller)}
        </Text>
        <Text style={[styles.chevron, { color: palette.tint }]}>›</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    borderWidth: 1,
    borderRadius: AppTheme.radius.md,
    flexDirection: "row",
    alignItems: "center",
    padding: AppTheme.spacing.md,
    gap: AppTheme.spacing.md,
  },
  iconContainer: {
    width: 42,
    height: 42,
    borderRadius: AppTheme.radius.md,
    alignItems: "center",
    justifyContent: "center",
  },
  icon: {
    fontSize: 18,
  },
  content: {
    flex: 1,
    gap: 4,
  },
  title: {
    fontSize: 15,
    fontWeight: "700",
  },
  meta: {
    fontSize: 13,
    fontWeight: "500",
  },
  trailing: {
    alignItems: "flex-end",
    gap: 4,
  },
  seller: {
    fontSize: 11,
    fontWeight: "600",
  },
  chevron: {
    fontSize: 22,
    fontWeight: "700",
  },
});

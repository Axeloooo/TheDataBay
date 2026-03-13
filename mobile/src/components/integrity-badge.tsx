import React from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import type { IntegrityStatus } from "@/src/lib/integrity";

type Props = {
  status: IntegrityStatus;
  detail?: string;
};

const CONFIG: Record<
  IntegrityStatus,
  { label: string; color: string; bg: string }
> = {
  verifying: { label: "Verifying…", color: "#687076", bg: "#F2F2F7" },
  verified: { label: "✓ Verified", color: "#34C759", bg: "#E8FAE8" },
  failed: { label: "✕ Integrity Failed", color: "#FF3B30", bg: "#FEECEB" },
  unavailable: {
    label: "— Integrity Unavailable",
    color: "#FF9500",
    bg: "#FFF3E0",
  },
};

export default function IntegrityBadge({ status, detail }: Props) {
  const { label, color, bg } = CONFIG[status];

  return (
    <View style={[styles.container, { backgroundColor: bg }]}>
      <View style={styles.row}>
        {status === "verifying" && (
          <ActivityIndicator
            size="small"
            color={color}
            style={styles.spinner}
          />
        )}
        <Text style={[styles.label, { color }]}>{label}</Text>
      </View>
      {detail && <Text style={styles.detail}>{detail}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
  },
  spinner: {
    marginRight: 6,
  },
  label: {
    fontSize: 13,
    fontWeight: "600",
  },
  detail: {
    fontSize: 12,
    color: "#687076",
    marginTop: 4,
  },
});

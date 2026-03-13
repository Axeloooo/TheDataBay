import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";

type StatusPillProps = {
  label: string;
  tone?: "info" | "success" | "warning" | "danger";
};

export function StatusPill({ label, tone = "info" }: StatusPillProps) {
  const palette = useAppTheme();
  const color =
    tone === "success"
      ? palette.success
      : tone === "warning"
        ? palette.warning
        : tone === "danger"
          ? palette.danger
          : palette.tint;

  return (
    <View
      style={[
        styles.pill,
        { backgroundColor: `${color}18`, borderColor: `${color}40` },
      ]}
    >
      <View style={[styles.dot, { backgroundColor: color }]} />
      <Text style={[styles.label, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    alignSelf: "flex-start",
    borderRadius: AppTheme.radius.pill,
    borderWidth: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 999,
  },
  label: {
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 0.2,
  },
});

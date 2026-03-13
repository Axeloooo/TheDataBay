import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";
import { AppButton } from "@/components/ui/app-button";
import { SurfaceCard } from "@/components/ui/surface-card";

type Props = {
  title?: string;
  message: string;
  onRetry?: () => void;
};

export default function ErrorPanel({
  title = "Something went wrong",
  message,
  onRetry,
}: Props) {
  const palette = useAppTheme();

  return (
    <SurfaceCard muted style={styles.card}>
      <View
        style={[styles.iconWrap, { backgroundColor: `${palette.danger}18` }]}
      >
        <Text style={styles.icon}>!</Text>
      </View>
      <Text style={[styles.title, { color: palette.text }]}>{title}</Text>
      <Text style={[styles.message, { color: palette.subtleText }]}>
        {message}
      </Text>
      {onRetry ? (
        <AppButton label="Try Again" onPress={onRetry} style={styles.button} />
      ) : null}
    </SurfaceCard>
  );
}

const styles = StyleSheet.create({
  card: {
    alignItems: "center",
    gap: AppTheme.spacing.md,
  },
  iconWrap: {
    width: 52,
    height: 52,
    borderRadius: 999,
    alignItems: "center",
    justifyContent: "center",
  },
  icon: {
    fontSize: 26,
    fontWeight: "800",
  },
  title: {
    fontSize: 18,
    fontWeight: "800",
  },
  message: {
    fontSize: 14,
    lineHeight: 21,
    textAlign: "center",
  },
  button: {
    alignSelf: "stretch",
  },
});

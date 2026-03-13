import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, View } from "react-native";

import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";

export default function SkeletonCard() {
  const palette = useAppTheme();
  const opacity = useRef(new Animated.Value(0.35)).current;

  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: 1,
          duration: 850,
          useNativeDriver: true,
        }),
        Animated.timing(opacity, {
          toValue: 0.35,
          duration: 850,
          useNativeDriver: true,
        }),
      ]),
    );

    animation.start();
    return () => animation.stop();
  }, [opacity]);

  return (
    <Animated.View
      style={[
        styles.card,
        AppTheme.shadow.soft,
        {
          opacity,
          backgroundColor: palette.card,
          borderColor: palette.border,
        },
      ]}
    >
      <View style={[styles.titleLine, { backgroundColor: palette.surface }]} />
      <View style={[styles.descLine, { backgroundColor: palette.surface }]} />
      <View
        style={[styles.descLineWide, { backgroundColor: palette.surface }]}
      />
      <View style={styles.footer}>
        <View style={[styles.metaLine, { backgroundColor: palette.surface }]} />
        <View
          style={[styles.metaLineShort, { backgroundColor: palette.surface }]}
        />
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: AppTheme.radius.lg,
    padding: AppTheme.spacing.lg,
    gap: AppTheme.spacing.md,
  },
  titleLine: {
    height: 20,
    borderRadius: 10,
    width: "68%",
  },
  descLine: {
    height: 14,
    borderRadius: 10,
    width: "100%",
  },
  descLineWide: {
    height: 14,
    borderRadius: 10,
    width: "86%",
  },
  footer: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: AppTheme.spacing.sm,
  },
  metaLine: {
    height: 12,
    borderRadius: 10,
    width: "34%",
  },
  metaLineShort: {
    height: 12,
    borderRadius: 10,
    width: "22%",
  },
});

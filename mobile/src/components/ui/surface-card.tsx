import React from "react";
import {
  StyleSheet,
  View,
  type StyleProp,
  type ViewProps,
  type ViewStyle,
} from "react-native";

import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";

type SurfaceCardProps = ViewProps & {
  style?: StyleProp<ViewStyle>;
  muted?: boolean;
};

export function SurfaceCard({
  children,
  style,
  muted = false,
  ...props
}: SurfaceCardProps) {
  const palette = useAppTheme();

  return (
    <View
      {...props}
      style={[
        styles.card,
        AppTheme.shadow.card,
        {
          backgroundColor: muted ? palette.cardMuted : palette.card,
          borderColor: palette.border,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: AppTheme.radius.lg,
    borderWidth: 1,
    padding: AppTheme.spacing.lg,
  },
});

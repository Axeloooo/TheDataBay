import React from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  type StyleProp,
  type ViewStyle,
} from "react-native";

import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";

type AppButtonProps = {
  label: string;
  onPress?: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  style?: StyleProp<ViewStyle>;
};

export function AppButton({
  label,
  onPress,
  disabled = false,
  loading = false,
  variant = "primary",
  style,
}: AppButtonProps) {
  const palette = useAppTheme();
  const isDisabled = disabled || loading;

  const backgroundColor =
    variant === "primary"
      ? palette.tint
      : variant === "secondary"
        ? palette.cardMuted
        : variant === "danger"
          ? palette.danger
          : "transparent";

  const textColor =
    variant === "ghost"
      ? palette.text
      : variant === "secondary"
        ? palette.text
        : "#ffffff";

  return (
    <Pressable
      disabled={isDisabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        {
          backgroundColor,
          borderColor: variant === "ghost" ? palette.border : backgroundColor,
          opacity: isDisabled ? 0.5 : pressed ? 0.88 : 1,
        },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={textColor} />
      ) : (
        <Text style={[styles.label, { color: textColor }]}>{label}</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: 48,
    borderRadius: AppTheme.radius.md,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: AppTheme.spacing.lg,
  },
  label: {
    fontSize: 15,
    fontWeight: "700",
  },
});

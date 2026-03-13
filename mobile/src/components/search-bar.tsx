import React, { useRef } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";

type Props = {
  value: string;
  onChangeText: (text: string) => void;
  onSubmit: () => void;
  onClear: () => void;
  placeholder?: string;
  autoFocus?: boolean;
};

export default function SearchBar({
  value,
  onChangeText,
  onSubmit,
  onClear,
  placeholder = "Search datasets by meaning, not keywords",
  autoFocus = false,
}: Props) {
  const palette = useAppTheme();
  const inputRef = useRef<TextInput>(null);

  return (
    <View
      style={[
        styles.shell,
        {
          backgroundColor: palette.card,
          borderColor: palette.border,
        },
      ]}
    >
      <View style={[styles.inputRow, { backgroundColor: palette.cardMuted }]}>
        <Text style={[styles.icon, { color: palette.subtleText }]}>⌕</Text>
        <TextInput
          ref={inputRef}
          style={[styles.input, { color: palette.text }]}
          value={value}
          onChangeText={onChangeText}
          onSubmitEditing={onSubmit}
          placeholder={placeholder}
          placeholderTextColor={palette.subtleText}
          returnKeyType="search"
          autoFocus={autoFocus}
          autoCapitalize="none"
          autoCorrect={false}
          clearButtonMode="never"
        />
        {value.length > 0 && (
          <Pressable
            onPress={() => {
              onClear();
              inputRef.current?.focus();
            }}
            style={({ pressed }) => [
              styles.clearButton,
              { opacity: pressed ? 0.7 : 1 },
            ]}
            hitSlop={12}
          >
            <Text style={[styles.clearText, { color: palette.subtleText }]}>
              ✕
            </Text>
          </Pressable>
        )}
      </View>
      <Pressable
        style={({ pressed }) => [
          styles.searchButton,
          {
            backgroundColor: value.trim() ? palette.tint : palette.surface,
            opacity: pressed ? 0.88 : 1,
          },
        ]}
        onPress={onSubmit}
        disabled={!value.trim()}
      >
        <Text
          style={[
            styles.searchButtonText,
            { color: value.trim() ? "#ffffff" : palette.subtleText },
          ]}
        >
          Search
        </Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  shell: {
    borderWidth: 1,
    borderRadius: AppTheme.radius.xl,
    padding: AppTheme.spacing.sm,
    gap: AppTheme.spacing.sm,
  },
  inputRow: {
    minHeight: 54,
    borderRadius: AppTheme.radius.md,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: AppTheme.spacing.md,
    gap: AppTheme.spacing.sm,
  },
  icon: {
    fontSize: 18,
    fontWeight: "700",
  },
  input: {
    flex: 1,
    fontSize: 15,
    fontWeight: "500",
    paddingVertical: 0,
  },
  clearButton: {
    width: 28,
    height: 28,
    borderRadius: 999,
    alignItems: "center",
    justifyContent: "center",
  },
  clearText: {
    fontSize: 14,
    fontWeight: "700",
  },
  searchButton: {
    minHeight: 46,
    borderRadius: AppTheme.radius.md,
    alignItems: "center",
    justifyContent: "center",
  },
  searchButtonText: {
    fontSize: 15,
    fontWeight: "700",
  },
});

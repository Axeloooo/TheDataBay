import {
  DarkTheme,
  DefaultTheme,
  ThemeProvider,
} from "@react-navigation/native";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import "react-native-reanimated";

import { WalletSync } from "@/components/wallet-sync";
import { Colors } from "@/constants/theme";
import { useColorScheme } from "@/hooks/use-color-scheme";
import { WalletAppKitProvider } from "@/src/lib/appkit";
import { useCurrencyStore } from "@/src/stores/currency-store";
import { useMarketplaceStore } from "@/src/stores/marketplace-store";
import { useWalletStore } from "@/src/stores/wallet-store";

export const unstable_settings = {
  anchor: "(tabs)",
};

function StoreBootstrap() {
  const startRatesPolling = useCurrencyStore((s) => s.startRatesPolling);
  const stopRatesPolling = useCurrencyStore((s) => s.stopRatesPolling);
  const fetchItems = useMarketplaceStore((s) => s.fetchItems);
  const refreshSession = useWalletStore((s) => s.refreshSession);

  useEffect(() => {
    void fetchItems();
    void refreshSession();
    startRatesPolling();

    return () => {
      stopRatesPolling();
    };
  }, [fetchItems, refreshSession, startRatesPolling, stopRatesPolling]);

  return null;
}

export default function RootLayout() {
  const colorScheme = useColorScheme();
  const palette = Colors[colorScheme ?? "light"];
  const navigationTheme = colorScheme === "dark" ? DarkTheme : DefaultTheme;
  const themedNavigation = {
    ...navigationTheme,
    colors: {
      ...navigationTheme.colors,
      background: palette.background,
      card: palette.card,
      border: palette.border,
      primary: palette.tint,
      text: palette.text,
      notification: palette.warning,
    },
  };

  return (
    <ThemeProvider value={themedNavigation}>
      <WalletAppKitProvider sync={<WalletSync />}>
        <StoreBootstrap />
        <Stack>
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen
            name="dataset/[id]"
            options={{
              title: "Dataset",
              headerBackTitle: "Marketplace",
              contentStyle: { backgroundColor: palette.background },
            }}
          />
          <Stack.Screen name="+not-found" />
        </Stack>
        <StatusBar style={colorScheme === "dark" ? "light" : "dark"} />
      </WalletAppKitProvider>
    </ThemeProvider>
  );
}

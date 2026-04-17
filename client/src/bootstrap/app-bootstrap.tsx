import { useEffect } from "react";
import { useCurrencyStore } from "@/stores/currency-store";
import { useSearchStore } from "@/stores/search-store";
import { useThemeStore } from "@/stores/theme-store";
import { useWalletStore } from "@/stores/wallet-store";

export function AppBootstrap() {
  const theme = useThemeStore((state) => state.theme);
  const applyTheme = useThemeStore((state) => state.applyTheme);
  const restoreSession = useWalletStore((state) => state.restoreSession);
  const subscribeToRuntime = useWalletStore(
    (state) => state.subscribeToRuntime,
  );
  const startRatesPolling = useCurrencyStore(
    (state) => state.startRatesPolling,
  );
  const stopRatesPolling = useCurrencyStore((state) => state.stopRatesPolling);
  const resetOnAppStart = useSearchStore((state) => state.resetOnAppStart);

  useEffect(() => {
    resetOnAppStart();
  }, [resetOnAppStart]);

  useEffect(() => {
    applyTheme(theme);
  }, [theme, applyTheme]);

  useEffect(() => {
    void restoreSession();
    const unsubscribe = subscribeToRuntime();
    startRatesPolling();

    return () => {
      unsubscribe();
      stopRatesPolling();
    };
  }, [restoreSession, subscribeToRuntime, startRatesPolling, stopRatesPolling]);

  return null;
}

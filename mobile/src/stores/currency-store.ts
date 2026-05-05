import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  type DisplayCurrency,
  type FxRates,
  fetchFxRates,
  loadCachedFxRates,
} from "@/src/lib/fx";

type CurrencyStore = {
  displayCurrency: DisplayCurrency;
  rates: FxRates | null;
  ratesUnavailable: boolean;
  pollingIntervalId: ReturnType<typeof setInterval> | null;
  setDisplayCurrency: (currency: DisplayCurrency) => void;
  refreshRates: () => Promise<void>;
  startRatesPolling: () => void;
  stopRatesPolling: () => void;
};

const STORAGE_KEY = "thedatabay_preferred_currency_v1";

function normalizeCurrency(raw: string): DisplayCurrency {
  switch (raw.trim()) {
    case "USDC":
    case "USD":
    case "CAD":
    case "MXN":
    case "EUR":
    case "ETH":
    case "SOL":
    case "CNY":
    case "USDT":
      return raw.trim() as DisplayCurrency;
    default:
      return "USDC";
  }
}

export const useCurrencyStore = create<CurrencyStore>()(
  persist(
    (set, get) => ({
      displayCurrency: "USDC",
      rates: null,
      ratesUnavailable: false,
      pollingIntervalId: null,

      setDisplayCurrency: (currency) => {
        set({ displayCurrency: currency });
      },

      refreshRates: async () => {
        try {
          const fetched = await fetchFxRates();
          set({ rates: fetched, ratesUnavailable: false });
        } catch {
          const cached = await loadCachedFxRates(60 * 60_000);
          set({ rates: cached, ratesUnavailable: !cached });
        }
      },

      startRatesPolling: () => {
        const existing = get().pollingIntervalId;
        if (existing !== null) return;

        void get().refreshRates();
        const intervalId = setInterval(() => {
          void get().refreshRates();
        }, 60_000);
        set({ pollingIntervalId: intervalId });
      },

      stopRatesPolling: () => {
        const existing = get().pollingIntervalId;
        if (existing === null) return;
        clearInterval(existing);
        set({ pollingIntervalId: null });
      },
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({
        displayCurrency: state.displayCurrency,
      }),
      merge: (persistedState, currentState) => {
        const persisted = persistedState as Partial<CurrencyStore> | undefined;
        return {
          ...currentState,
          ...persisted,
          displayCurrency: normalizeCurrency(
            String(persisted?.displayCurrency ?? currentState.displayCurrency),
          ),
        };
      },
    },
  ),
);

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
  preferredCurrency: DisplayCurrency;
  rates: FxRates | null;
  ratesUnavailable: boolean;
  pollingIntervalId: ReturnType<typeof setInterval> | null;
  setPreferredCurrency: (currency: DisplayCurrency) => void;
  refreshRates: () => Promise<void>;
  startRatesPolling: () => void;
  stopRatesPolling: () => void;
};

const STORAGE_KEY = "bridgemart_preferred_currency_v1";

export const useCurrencyStore = create<CurrencyStore>()(
  persist(
    (set, get) => ({
      preferredCurrency: "ETH",
      rates: null,
      ratesUnavailable: false,
      pollingIntervalId: null,

      setPreferredCurrency: (currency) => {
        set({ preferredCurrency: currency });
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
        preferredCurrency: state.preferredCurrency,
      }),
    },
  ),
);

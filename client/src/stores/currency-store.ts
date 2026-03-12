import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import {
  type DisplayCurrency,
  type FxRates,
  fetchFxRates,
  loadCachedFxRates,
} from "@/lib/fx";
import { ensurePersistFormat } from "@/stores/persist-utils";

type CurrencyPersistedState = {
  preferredCurrency: DisplayCurrency;
};

type CurrencyStore = {
  preferredCurrency: DisplayCurrency;
  rates: FxRates | null;
  ratesUnavailable: boolean;
  pollingIntervalId: number | null;
  setPreferredCurrency: (currency: DisplayCurrency) => void;
  refreshRates: () => Promise<void>;
  startRatesPolling: () => void;
  stopRatesPolling: () => void;
};

const STORAGE_KEY = "bridgemart_preferred_currency_v1";

function normalizeCurrency(raw: string): DisplayCurrency {
  switch (raw.trim()) {
    case "CAD":
    case "USD":
    case "EUR":
    case "USDC":
    case "SOL":
    case "ETH":
      return raw.trim() as DisplayCurrency;
    default:
      return "ETH";
  }
}

ensurePersistFormat<CurrencyPersistedState>(STORAGE_KEY, (raw) => ({
  preferredCurrency: normalizeCurrency(raw),
}));

export const useCurrencyStore = create<CurrencyStore>()(
  persist(
    (set, get) => ({
      preferredCurrency: "ETH",
      rates: loadCachedFxRates(10 * 60_000),
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
          const cached = loadCachedFxRates(60 * 60_000);
          set({ rates: cached, ratesUnavailable: !cached });
        }
      },
      startRatesPolling: () => {
        const existing = get().pollingIntervalId;
        if (existing !== null) return;

        void get().refreshRates();
        const intervalId = window.setInterval(() => {
          void get().refreshRates();
        }, 60_000);
        set({ pollingIntervalId: intervalId });
      },
      stopRatesPolling: () => {
        const existing = get().pollingIntervalId;
        if (existing === null) return;
        window.clearInterval(existing);
        set({ pollingIntervalId: null });
      },
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        preferredCurrency: state.preferredCurrency,
      }),
    },
  ),
);

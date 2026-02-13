import { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
  type DisplayCurrency,
  type FxRates,
  fetchFxRates,
  loadCachedFxRates,
} from "@/lib/fx";

type CurrencyContextValue = {
  preferredCurrency: DisplayCurrency;
  setPreferredCurrency: (currency: DisplayCurrency) => void;
  rates: FxRates | null;
  ratesUnavailable: boolean;
};

const STORAGE_KEY = "bridgemart_preferred_currency_v1";

const CurrencyContext = createContext<CurrencyContextValue | null>(null);

export function CurrencyProvider({ children }: { children: React.ReactNode }) {
  const [preferredCurrency, setPreferredCurrencyState] = useState<DisplayCurrency>(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as DisplayCurrency | null;
    return saved ?? "ETH";
  });
  const [rates, setRates] = useState<FxRates | null>(() => loadCachedFxRates(10 * 60_000));
  const [ratesUnavailable, setRatesUnavailable] = useState(false);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, preferredCurrency);
  }, [preferredCurrency]);

  useEffect(() => {
    let active = true;

    const loadRates = async () => {
      try {
        const fetched = await fetchFxRates();
        if (!active) return;
        setRates(fetched);
        setRatesUnavailable(false);
      } catch {
        if (!active) return;
        const cached = loadCachedFxRates(60 * 60_000);
        setRates(cached);
        setRatesUnavailable(!cached);
      }
    };

    void loadRates();
    const interval = window.setInterval(() => {
      void loadRates();
    }, 60_000);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  const setPreferredCurrency = (currency: DisplayCurrency) => {
    setPreferredCurrencyState(currency);
  };

  const value = useMemo(
    () => ({
      preferredCurrency,
      setPreferredCurrency,
      rates,
      ratesUnavailable,
    }),
    [preferredCurrency, rates, ratesUnavailable],
  );

  return (
    <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>
  );
}

export function useCurrency() {
  const ctx = useContext(CurrencyContext);
  if (!ctx) throw new Error("useCurrency must be used within CurrencyProvider");
  return ctx;
}

import {
  convertSettlementToCurrency,
  formatCurrencyAmount,
} from "../../src/lib/fx";
import type { FxRates } from "../../src/lib/fx";

const mockRates: FxRates = {
  ethUsd: 2000,
  ethCad: 2700,
  ethEur: 1800,
  ethMxn: 34000,
  ethUsdc: 2000,
  ethSol: 50,
  ethCny: 14000,
  ethUsdt: 2000,
  usdcUsd: 1,
  updatedAt: Date.now(),
};

describe("convertSettlementToCurrency", () => {
  it("returns the settlement amount as-is for USDC currency", () => {
    expect(
      convertSettlementToCurrency("1000000", 6, "USDC", mockRates),
    ).toBe(1);
  });

  it("converts settlement USDC to USD", () => {
    expect(
      convertSettlementToCurrency("1000000", 6, "USD", mockRates),
    ).toBe(1);
  });

  it("converts settlement USDC to CAD", () => {
    expect(
      convertSettlementToCurrency("1000000", 6, "CAD", mockRates),
    ).toBe(2700 / 2000);
  });

  it("converts settlement USDC to EUR", () => {
    expect(
      convertSettlementToCurrency("1000000", 6, "EUR", mockRates),
    ).toBe(1800 / 2000);
  });

  it("converts settlement USDC to MXN", () => {
    expect(
      convertSettlementToCurrency("1000000", 6, "MXN", mockRates),
    ).toBe(34000 / 2000);
  });

  it("converts settlement USDC to SOL", () => {
    expect(
      convertSettlementToCurrency("1000000", 6, "SOL", mockRates),
    ).toBe(50 / 2000);
  });

  it("converts settlement USDC to CNY", () => {
    expect(
      convertSettlementToCurrency("1000000", 6, "CNY", mockRates),
    ).toBe(14000 / 2000);
  });

  it("converts settlement USDC to USDT", () => {
    expect(
      convertSettlementToCurrency("1000000", 6, "USDT", mockRates),
    ).toBe(1);
  });

  it("returns null when rates are null (non-USDC currency)", () => {
    expect(convertSettlementToCurrency("1000000", 6, "USD", null)).toBeNull();
  });

  it("returns null for invalid atomic amounts", () => {
    expect(
      convertSettlementToCurrency("not-a-number", 6, "USD", mockRates),
    ).toBeNull();
  });

  it("returns null for SOL when the rate is unavailable", () => {
    const ratesNoSol: FxRates = { ...mockRates, ethSol: 0 };
    expect(
      convertSettlementToCurrency("1000000", 6, "SOL", ratesNoSol),
    ).toBeNull();
  });
});

describe("formatCurrencyAmount", () => {
  it("formats ETH with symbol", () => {
    const result = formatCurrencyAmount(1.5, "ETH");
    expect(result).toContain("ETH");
    expect(result).toContain("1.5");
  });

  it("formats SOL with symbol", () => {
    const result = formatCurrencyAmount(50, "SOL");
    expect(result).toContain("SOL");
  });

  it("formats USDT with symbol", () => {
    const result = formatCurrencyAmount(12.5, "USDT");
    expect(result).toContain("USDT");
  });

  it("formats USD as currency", () => {
    const result = formatCurrencyAmount(2000, "USD");
    // Intl.NumberFormat output varies; just check it contains the number
    expect(result).toContain("2,000");
  });

  it("formats MXN as currency", () => {
    const result = formatCurrencyAmount(34000, "MXN");
    expect(result).toContain("34,000");
  });
});

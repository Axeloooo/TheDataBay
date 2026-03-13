import { convertEthToCurrency, formatCurrencyAmount } from "../../src/lib/fx";
import type { FxRates, DisplayCurrency } from "../../src/lib/fx";

const mockRates: FxRates = {
  ethUsd: 2000,
  ethCad: 2700,
  ethEur: 1800,
  ethUsdc: 2000,
  ethSol: 50,
  updatedAt: Date.now(),
};

describe("convertEthToCurrency", () => {
  it("returns the eth amount as-is for ETH currency", () => {
    expect(convertEthToCurrency(1, "ETH", mockRates)).toBe(1);
  });

  it("converts ETH to USD", () => {
    expect(convertEthToCurrency(1, "USD", mockRates)).toBe(2000);
  });

  it("converts ETH to CAD", () => {
    expect(convertEthToCurrency(0.5, "CAD", mockRates)).toBe(1350);
  });

  it("converts ETH to EUR", () => {
    expect(convertEthToCurrency(2, "EUR", mockRates)).toBe(3600);
  });

  it("converts ETH to USDC", () => {
    expect(convertEthToCurrency(1, "USDC", mockRates)).toBe(2000);
  });

  it("converts ETH to SOL", () => {
    expect(convertEthToCurrency(1, "SOL", mockRates)).toBe(50);
  });

  it("returns null when rates are null (non-ETH currency)", () => {
    expect(convertEthToCurrency(1, "USD", null)).toBeNull();
  });

  it("returns null for non-finite ethAmount", () => {
    expect(convertEthToCurrency(NaN, "USD", mockRates)).toBeNull();
    expect(convertEthToCurrency(Infinity, "USD", mockRates)).toBeNull();
  });

  it("returns ETH amount even when rates are null", () => {
    expect(convertEthToCurrency(1.5, "ETH", null)).toBe(1.5);
  });

  it("returns null for SOL when ethSol is 0", () => {
    const ratesNoSol: FxRates = { ...mockRates, ethSol: 0 };
    expect(convertEthToCurrency(1, "SOL", ratesNoSol)).toBeNull();
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

  it("formats USD as currency", () => {
    const result = formatCurrencyAmount(2000, "USD");
    // Intl.NumberFormat output varies; just check it contains the number
    expect(result).toContain("2,000");
  });
});

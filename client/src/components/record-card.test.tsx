import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import RecordCard from "./record-card";
import type { CardDataset } from "@/types/ai";
import { normalizeMarketplacePrice } from "@/lib/marketplace";

vi.mock("@/stores/currency-store", () => ({
  useCurrencyStore: (
    selector: (s: { preferredCurrency: string; rates: null }) => unknown,
  ) => selector({ preferredCurrency: "USDC", rates: null }),
}));

const browseDataset: CardDataset = {
  id: "abc-123",
  title: "Global Trade Dataset",
  description: "Comprehensive trade flows across 50 markets.",
  price_atomic: "5000000",
  settlement_currency: "USDC",
  settlement_decimals: 6,
  purchase_count: 42,
};

const searchDataset: CardDataset = {
  id: "def-456",
  title: "Climate Data 2024",
  description: "Temperature anomalies and sea-level records.",
  price_atomic: "2000000",
  settlement_currency: "USDC",
  settlement_decimals: 6,
};

const cadcDataset: CardDataset = {
  id: "ghi-789",
  title: "Canadian Market Data",
  description: "Aggregated CAD-denominated market data.",
  price_atomic: "5000000000000000000",
  settlement_currency: "CADC",
  settlement_decimals: 18,
  purchase_count: 7,
};

function renderCard(props: Parameters<typeof RecordCard>[0]) {
  return render(
    <MemoryRouter>
      <RecordCard {...props} />
    </MemoryRouter>,
  );
}

describe("RecordCard score badge", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders no score badge when score prop is absent", () => {
    renderCard({ dataset: browseDataset });
    expect(screen.queryByText(/match/i)).toBeNull();
  });

  it("renders High match badge with success variant for high score", () => {
    renderCard({ dataset: searchDataset, score: 0.85, scoreLabel: "high" });
    const badge = screen.getByText("High match");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toMatch(/green/);
  });

  it("renders Moderate match badge with warning variant for moderate score", () => {
    renderCard({ dataset: searchDataset, score: 0.5, scoreLabel: "moderate" });
    const badge = screen.getByText("Moderate match");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toMatch(/orange/);
  });

  it("renders Low match badge with destructive variant for low score of 0", () => {
    renderCard({ dataset: searchDataset, score: 0, scoreLabel: "low" });
    const badge = screen.getByText("Low match");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toMatch(/destructive/);
  });

  it("renders no badge when score is undefined even if scoreLabel is set", () => {
    renderCard({ dataset: searchDataset, scoreLabel: "high" });
    expect(screen.queryByText(/match/i)).toBeNull();
  });

  it("browse fixture shows purchase_count and no score badge", () => {
    renderCard({ dataset: browseDataset });
    expect(screen.getByText(/42 purchases/)).toBeInTheDocument();
    expect(screen.queryByText(/match/i)).toBeNull();
  });

  it("search result without purchase_count shows no purchases line", () => {
    renderCard({ dataset: searchDataset, score: 0.7, scoreLabel: "high" });
    expect(screen.queryByText(/purchases/)).toBeNull();
  });
});

describe("RecordCard settlement token logo", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders usdc-logo.svg for USDC listing", () => {
    const { container } = renderCard({ dataset: browseDataset });
    const imgs = container.querySelectorAll("img");
    const settlementLogo = Array.from(imgs).find((img) =>
      img.src.includes("usdc-logo.svg"),
    );
    expect(settlementLogo).toBeDefined();
  });

  it("renders cadc-logo.svg for CADC listing", () => {
    const { container } = renderCard({ dataset: cadcDataset });
    const imgs = container.querySelectorAll("img");
    const cadcLogo = Array.from(imgs).find((img) =>
      img.src.includes("cadc-logo.svg"),
    );
    expect(cadcLogo).toBeDefined();
  });

  it("shows CADC purchase_count", () => {
    renderCard({ dataset: cadcDataset });
    expect(screen.getByText(/7 purchases/)).toBeInTheDocument();
  });
});

describe("normalizeMarketplacePrice", () => {
  it("returns USDC with 6 decimals for USDC item", () => {
    const result = normalizeMarketplacePrice({
      price_atomic: "5000000",
      settlement_currency: "USDC",
      settlement_decimals: 6,
    });
    expect(result.settlementCurrency).toBe("USDC");
    expect(result.settlementDecimals).toBe(6);
    expect(result.settlementAmount).toBe("5");
  });

  it("returns CADC with 18 decimals for CADC item", () => {
    const result = normalizeMarketplacePrice({
      price_atomic: "5000000000000000000",
      settlement_currency: "CADC",
      settlement_decimals: 18,
    });
    expect(result.settlementCurrency).toBe("CADC");
    expect(result.settlementDecimals).toBe(18);
    expect(result.settlementAmount).toBe("5");
  });

  it("falls back to USDC and 6 decimals when currency is missing", () => {
    const result = normalizeMarketplacePrice({
      price_atomic: "1000000",
    });
    expect(result.settlementCurrency).toBe("USDC");
    expect(result.settlementDecimals).toBe(6);
    expect(result.settlementAmount).toBe("1");
  });

  it("derives CADC decimals (18) from currency when settlement_decimals is missing", () => {
    const result = normalizeMarketplacePrice({
      price_atomic: "1000000000000000000",
      settlement_currency: "CADC",
    });
    expect(result.settlementCurrency).toBe("CADC");
    expect(result.settlementDecimals).toBe(18);
    expect(result.settlementAmount).toBe("1");
  });

  it("falls back to USDC for unknown currency", () => {
    const result = normalizeMarketplacePrice({
      price_atomic: "2000000",
      settlement_currency: "XYZ" as "USDC",
    });
    expect(result.settlementCurrency).toBe("USDC");
  });
});

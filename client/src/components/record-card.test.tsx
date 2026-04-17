import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import RecordCard from "./record-card";
import type { CardDataset } from "@/types/ai";

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

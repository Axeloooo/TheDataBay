import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import SellerDashboard from "./SellerDashboard";
import type { SellerListing } from "@/types/me";

const getMyListings = vi.fn();
let connected = true;

vi.mock("@/lib/backend", () => ({
  backend: { getMyListings: () => getMyListings() },
}));
vi.mock("@/stores/wallet-store", () => ({
  useWalletStore: (
    selector: (s: { isConnected: boolean; address: string | null }) => unknown,
  ) =>
    selector({
      isConnected: connected,
      address: connected ? "0xabc" : null,
    }),
}));

const USDC = "0x" + "0A".repeat(20);

const base: SellerListing = {
  listing_id: "0x" + "01".repeat(16) + "00".repeat(16),
  title: "Unsold set",
  price: "5000000",
  payment_token: USDC,
  token_symbol: "USDC",
  token_decimals: 6,
  sales_count: 0,
  earnings_by_token: {},
  price_editable: true,
  source: "indexer",
};
const sold: SellerListing = {
  ...base,
  listing_id: "0x" + "02".repeat(16) + "00".repeat(16),
  title: "Sold set",
  sales_count: 2,
  earnings_by_token: { [USDC]: "2000000" },
  price_editable: false,
};

function renderPage() {
  return render(
    <MemoryRouter>
      <SellerDashboard />
    </MemoryRouter>,
  );
}

describe("SellerDashboard", () => {
  beforeEach(() => {
    getMyListings.mockReset();
    connected = true;
  });

  it("shows an empty state for a wallet with no listings", async () => {
    getMyListings.mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText(/haven't listed any datasets/i)).toBeInTheDocument();
  });

  it("lists datasets with sales and earnings per token", async () => {
    getMyListings.mockResolvedValue([base, sold]);
    renderPage();
    expect(await screen.findByText("Sold set")).toBeInTheDocument();
    expect(screen.getByText("Unsold set")).toBeInTheDocument();
    expect(screen.getAllByText("2 USDC").length).toBeGreaterThan(0);
  });

  it("disables price editing for sold listings", async () => {
    getMyListings.mockResolvedValue([sold]);
    renderPage();
    const edit = await screen.findByRole("button", { name: /edit price/i });
    expect(edit).toBeDisabled();
    expect(screen.getByText(/can't change after the first sale/i)).toBeInTheDocument();
  });

  it("keeps price editing disabled for unsold listings until wallet-signed edits exist", async () => {
    getMyListings.mockResolvedValue([base]);
    renderPage();
    const edit = await screen.findByRole("button", { name: /edit price/i });
    expect(edit).toBeDisabled();
    expect(screen.getByText(/coming soon/i)).toBeInTheDocument();
  });

  it("shows an error panel when loading fails", async () => {
    getMyListings.mockRejectedValue(new Error("nope"));
    renderPage();
    expect(await screen.findByText("nope")).toBeInTheDocument();
  });

  it("notes that earnings need the indexer when served from the contract", async () => {
    getMyListings.mockResolvedValue([{ ...base, source: "contract" }]);
    renderPage();
    expect(await screen.findByText(/earnings are unavailable/i)).toBeInTheDocument();
  });
});

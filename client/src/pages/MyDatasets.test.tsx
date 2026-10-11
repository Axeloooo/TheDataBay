import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import MyDatasets from "./MyDatasets";
import type { PurchasedListing } from "@/types/me";

const getMyPurchases = vi.fn();
const download = vi.fn();
let connected = true;

vi.mock("@/lib/backend", () => ({
  backend: { getMyPurchases: () => getMyPurchases() },
}));
vi.mock("@/lib/dataset-download", () => ({
  downloadPurchasedDataset: (...args: unknown[]) => download(...args),
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
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const purchase: PurchasedListing = {
  listing_id: "0x" + "01".repeat(16) + "00".repeat(16),
  title: "Climate Data",
  description: "Temperature anomalies",
  dataset_url: "ipfs://cid",
  price_paid: "1010000",
  payment_token: "0x0A",
  token_symbol: "USDC",
  token_decimals: 6,
  purchased_at: "2026-10-11T00:00:00Z",
  source: "indexer",
};

function renderPage() {
  return render(
    <MemoryRouter>
      <MyDatasets />
    </MemoryRouter>,
  );
}

describe("MyDatasets", () => {
  beforeEach(() => {
    getMyPurchases.mockReset();
    download.mockReset();
    connected = true;
  });

  it("shows an empty state when the wallet has no purchases", async () => {
    getMyPurchases.mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText(/haven't bought any datasets/i)).toBeInTheDocument();
  });

  it("renders purchased datasets with the amount paid", async () => {
    getMyPurchases.mockResolvedValue([purchase]);
    renderPage();
    expect(await screen.findByText("Climate Data")).toBeInTheDocument();
    expect(screen.getByText("Temperature anomalies")).toBeInTheDocument();
    expect(screen.getByText(/1\.01 USDC/)).toBeInTheDocument();
  });

  it("runs the key release and decrypt flow on download", async () => {
    getMyPurchases.mockResolvedValue([purchase]);
    download.mockResolvedValue(undefined);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /download/i }));
    await waitFor(() =>
      expect(download).toHaveBeenCalledWith(
        purchase.listing_id,
        purchase.dataset_url,
        expect.any(Function),
      ),
    );
  });

  it("shows an error panel when loading fails", async () => {
    getMyPurchases.mockRejectedValue(new Error("boom"));
    renderPage();
    expect(await screen.findByText("boom")).toBeInTheDocument();
  });

  it("asks to connect a wallet when disconnected", () => {
    connected = false;
    renderPage();
    expect(screen.getByText(/connect your wallet/i)).toBeInTheDocument();
    expect(getMyPurchases).not.toHaveBeenCalled();
  });
});

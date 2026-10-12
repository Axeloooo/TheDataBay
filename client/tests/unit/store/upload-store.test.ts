import { beforeEach, describe, expect, it, vi } from "vitest";
import { useUploadStore } from "@/stores/upload-store";
import { backend } from "@/lib/backend";

vi.mock("sonner", () => ({
  toast: Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock("@/lib/backend", () => ({
  backend: {
    submitDataset: vi.fn(),
  },
}));

vi.mock("@/lib/marketplace", () => ({
  createItemTx: vi.fn(),
  getPaymentTokenAddressForCurrency: vi.fn(() => "0x0000000000000000000000000000000000000002"),
}));

vi.mock("@/lib/confetti", () => ({
  fireConfettiBurst: vi.fn(),
}));

const submitDataset = vi.mocked(backend.submitDataset);

function resetStore() {
  localStorage.clear();
  useUploadStore.setState({
    title: "",
    description: "",
    priceUsdc: "",
    settlementCurrency: "USDC",
    displayCurrency: "USDC",
    file: null,
    embedResult: null,
    loading: false,
    error: null,
    createTxHash: null,
    isCreating: false,
    persistedSession: null,
    hasInitialized: false,
  });
}

describe("upload-store synchronous dataset embed flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStore();
  });

  it("persists completed upload outputs from the synchronous response", async () => {
    submitDataset.mockResolvedValueOnce({
      listing_id: "123e4567-e89b-12d3-a456-426614174000",
      dataset_url: "ipfs://QmData",
      dataset_hash: "0xdata",
      preview: { column_names: ["age"], rows: [["63"]] },
      stats: {
        total_rows: 1,
        total_columns: 1,
        has_header: true,
        empty_rows_skipped: 0,
      },
      vector_spec: { model: "nomic-embed-text", dimension: 768 },
    });

    useUploadStore.setState({
      title: "Heart Data",
      description: "Rows",
      priceUsdc: "12.5",
      file: new File(["age\n63\n"], "heart.csv", { type: "text/csv" }),
    });

    await useUploadStore
      .getState()
      .submitUpload("0x0000000000000000000000000000000000000001");

    const state = useUploadStore.getState();
    expect(submitDataset).toHaveBeenCalledTimes(1);
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
    expect(state.embedResult?.listing_id).toBe(
      "123e4567-e89b-12d3-a456-426614174000",
    );
    expect(state.persistedSession?.datasetUrl).toBe("ipfs://QmData");
    expect(state.persistedSession?.status).toBe("completed");
  });

  it("stores the error message when synchronous upload fails", async () => {
    submitDataset.mockRejectedValueOnce(new Error("too many rows"));
    useUploadStore.setState({
      title: "Heart Data",
      description: "Rows",
      priceUsdc: "12.5",
      file: new File(["age\n63\n"], "heart.csv", { type: "text/csv" }),
    });

    await useUploadStore
      .getState()
      .submitUpload("0x0000000000000000000000000000000000000001");

    const state = useUploadStore.getState();
    expect(state.loading).toBe(false);
    expect(state.embedResult).toBeNull();
    expect(state.error).toBe("too many rows");
  });
});

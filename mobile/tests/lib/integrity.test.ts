import { verifyDatasetIntegrity } from "../../src/lib/integrity";

const DATASET_HASH = `0x${"11".repeat(32)}`;

describe("verifyDatasetIntegrity", () => {
  beforeEach(() => {
    global.fetch = jest.fn(async () => new Response("dataset-bytes")) as never;
    Object.defineProperty(global, "crypto", {
      configurable: true,
      value: {
        subtle: {
          digest: jest.fn(async () => new Uint8Array(32).fill(0x11).buffer),
        },
      },
    });
  });

  it("verifies dataset integrity without signature artifacts", async () => {
    const result = await verifyDatasetIntegrity({
      datasetUrl: "ipfs://dataset-cid",
      datasetHash: DATASET_HASH,
    });

    expect(result).toEqual({ status: "verified" });
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});

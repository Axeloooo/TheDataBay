import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { verifyDatasetIntegrity } from "../../../src/lib/integrity";

const DATASET_HASH = `0x${"11".repeat(32)}`;

describe("verifyDatasetIntegrity", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("dataset-bytes")),
    );
    vi.stubGlobal("crypto", {
      subtle: {
        digest: vi.fn(async () => new Uint8Array(32).fill(0x11).buffer),
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
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

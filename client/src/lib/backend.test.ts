import { beforeEach, describe, expect, it, vi } from "vitest";

const apiRequest = vi.fn();
const withSession = vi.fn();

vi.mock("@/lib/api", () => ({
  apiRequest: (...args: unknown[]) => apiRequest(...args),
}));
vi.mock("@/lib/auth", () => ({
  withSession: (call: (token: string) => Promise<unknown>) => withSession(call),
  authHeaders: (token: string) => ({ Authorization: `Bearer ${token}` }),
}));

import { backend } from "./backend";

describe("backend.reviewPurchaseRequest", () => {
  beforeEach(() => {
    apiRequest.mockReset().mockResolvedValue({ id: "req-1" });
    withSession
      .mockReset()
      .mockImplementation((call: (token: string) => Promise<unknown>) =>
        call("session-token"),
      );
  });

  it("sends the decision with the session token and no reviewer field", async () => {
    await backend.reviewPurchaseRequest("req-1", { status: "approved" });

    expect(withSession).toHaveBeenCalledTimes(1);
    expect(apiRequest).toHaveBeenCalledWith(
      "/api/v1/purchase-requests/req-1/review",
      {
        method: "POST",
        headers: { Authorization: "Bearer session-token" },
        body: JSON.stringify({ status: "approved" }),
      },
    );
  });

  it("drops a reviewed_by value smuggled in by a caller", async () => {
    await backend.reviewPurchaseRequest("req-1", {
      status: "rejected",
      reviewed_by: "0x0000000000000000000000000000000000000001",
    } as { status: "rejected" });

    const [, init] = apiRequest.mock.calls[0];
    expect(JSON.parse(init.body)).toEqual({ status: "rejected" });
  });
});

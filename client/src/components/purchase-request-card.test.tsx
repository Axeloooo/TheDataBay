import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { PurchaseRequestCard } from "./purchase-request-card";
import type { PurchaseRequest } from "@/types/agent";

const REQUESTER = "0xAa1Bb2Cc3Dd4Ee5Ff6Aa7Bb8Cc9Dd0Ee1Ff2Aa3B";
const OTHER = "0x9f8E7d6C5b4A3f2E1d0C9b8A7f6E5d4C3b2A1f0E";

function makeRequest(overrides: Partial<PurchaseRequest> = {}): PurchaseRequest {
  return {
    id: "req-1",
    agent_id: "agent-1",
    listing_id: "listing-1",
    requester_address: REQUESTER,
    status: "pending",
    reason: "Need benchmark data",
    reviewed_at: null,
    reviewed_by: null,
    created_at: "2026-10-01T00:00:00Z",
    updated_at: "2026-10-01T00:00:00Z",
    ...overrides,
  };
}

describe("PurchaseRequestCard", () => {
  it("lets the requester wallet review, ignoring address case", () => {
    const onApprove = vi.fn();
    const onReject = vi.fn();
    render(
      <PurchaseRequestCard
        request={makeRequest()}
        connectedAddress={REQUESTER.toLowerCase()}
        onApprove={onApprove}
        onReject={onReject}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /approve/i }));
    fireEvent.click(screen.getByRole("button", { name: /reject/i }));

    expect(onApprove).toHaveBeenCalledWith("req-1");
    expect(onReject).toHaveBeenCalledWith("req-1");
  });

  it("hides review actions from any other wallet", () => {
    render(
      <PurchaseRequestCard request={makeRequest()} connectedAddress={OTHER} />,
    );

    expect(screen.queryByRole("button", { name: /approve/i })).toBeNull();
    expect(
      screen.getByText("Only the requesting wallet can review this request."),
    ).toBeInTheDocument();
  });

  it("hides review actions when no wallet is connected", () => {
    render(<PurchaseRequestCard request={makeRequest()} connectedAddress={null} />);

    expect(screen.queryByRole("button", { name: /approve/i })).toBeNull();
    expect(
      screen.queryByText("Only the requesting wallet can review this request."),
    ).toBeNull();
  });

  it("hides review actions once the request is reviewed", () => {
    render(
      <PurchaseRequestCard
        request={makeRequest({ status: "approved", reviewed_by: REQUESTER })}
        connectedAddress={REQUESTER}
      />,
    );

    expect(screen.queryByRole("button", { name: /approve/i })).toBeNull();
  });
});

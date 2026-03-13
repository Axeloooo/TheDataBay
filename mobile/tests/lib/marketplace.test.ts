jest.mock("../../src/lib/appkit", () => ({
  getAppKit: jest.fn(() => null),
}));

import {
  weiToEth,
  isSameAddress,
  truncateAddress,
  formatPurchaseCount,
} from "../../src/lib/marketplace";

describe("weiToEth", () => {
  it("converts 1 ETH in wei", () => {
    const oneEth = "1000000000000000000";
    const result = parseFloat(weiToEth(oneEth));
    expect(result).toBeCloseTo(1, 5);
  });

  it("converts 0.5 ETH in wei", () => {
    const halfEth = "500000000000000000";
    const result = parseFloat(weiToEth(halfEth));
    expect(result).toBeCloseTo(0.5, 5);
  });

  it('returns "0" for invalid input', () => {
    expect(weiToEth("not-a-number")).toBe("0");
  });

  it("handles bigint input", () => {
    const result = parseFloat(weiToEth(1_000_000_000_000_000_000n));
    expect(result).toBeCloseTo(1, 5);
  });
});

describe("isSameAddress", () => {
  it("matches same-case addresses", () => {
    expect(isSameAddress("0xABC", "0xABC")).toBe(true);
  });

  it("is case-insensitive", () => {
    expect(isSameAddress("0xabc", "0xABC")).toBe(true);
  });

  it("returns false for different addresses", () => {
    expect(isSameAddress("0xabc", "0xdef")).toBe(false);
  });

  it("returns false when either is null", () => {
    expect(isSameAddress(null, "0xabc")).toBe(false);
    expect(isSameAddress("0xabc", null)).toBe(false);
  });

  it("returns false when both are null", () => {
    expect(isSameAddress(null, null)).toBe(false);
  });
});

describe("truncateAddress", () => {
  it("truncates a long address", () => {
    const addr = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef";
    const result = truncateAddress(addr, 4);
    expect(result).toBe("0xdead...beef");
  });

  it("returns short addresses as-is", () => {
    const short = "0x1234";
    expect(truncateAddress(short, 4)).toBe("0x1234");
  });
});

describe("formatPurchaseCount", () => {
  it("uses singular for 1", () => {
    expect(formatPurchaseCount(1)).toBe("1 purchase");
  });

  it("uses plural for 0", () => {
    expect(formatPurchaseCount(0)).toBe("0 purchases");
  });

  it("uses plural for 2+", () => {
    expect(formatPurchaseCount(42)).toBe("42 purchases");
  });
});

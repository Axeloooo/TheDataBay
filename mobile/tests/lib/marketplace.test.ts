jest.mock("../../src/lib/appkit", () => ({
  getAppKit: jest.fn(() => null),
}));

import {
  formatSettlementAmount,
  parseSettlementAmount,
  isSameAddress,
  truncateAddress,
  formatPurchaseCount,
} from "../../src/lib/marketplace";

describe("parseSettlementAmount", () => {
  it("converts 1 USDC to atomic units", () => {
    expect(parseSettlementAmount("1", 6)).toBe("1000000");
  });

  it("converts 0.5 USDC to atomic units", () => {
    expect(parseSettlementAmount("0.5", 6)).toBe("500000");
  });

  it("supports thousands separators", () => {
    expect(parseSettlementAmount("1,250.25", 6)).toBe("1250250000");
  });

  it("returns null for invalid input", () => {
    expect(parseSettlementAmount("not-a-number", 6)).toBeNull();
  });
});

describe("formatSettlementAmount", () => {
  it("formats atomic units into USDC", () => {
    expect(formatSettlementAmount("1000000", 6)).toBe("1");
  });

  it("formats fractional atomic units into USDC", () => {
    expect(formatSettlementAmount("500000", 6)).toBe("0.5");
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

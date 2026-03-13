import { uuidToBytes32, bytes32ToUuid } from "../../src/lib/ids";

describe("ids", () => {
  const VALID_UUID = "550e8400-e29b-41d4-a716-446655440000";
  const EXPECTED_BYTES32 =
    "0x550e8400e29b41d4a716446655440000" + "00000000000000000000000000000000";

  describe("uuidToBytes32", () => {
    it("converts a valid UUID to bytes32", () => {
      expect(uuidToBytes32(VALID_UUID)).toBe(EXPECTED_BYTES32);
    });

    it("lowercases hex output", () => {
      const upper = "550E8400-E29B-41D4-A716-446655440000";
      const result = uuidToBytes32(upper);
      expect(result).toBe(EXPECTED_BYTES32);
    });

    it("throws on invalid UUID format", () => {
      expect(() => uuidToBytes32("not-a-uuid")).toThrow("Invalid UUID format");
    });

    it("throws on empty string", () => {
      expect(() => uuidToBytes32("")).toThrow("Invalid UUID format");
    });
  });

  describe("bytes32ToUuid", () => {
    it("converts a valid bytes32 to UUID", () => {
      expect(bytes32ToUuid(EXPECTED_BYTES32)).toBe(VALID_UUID.toLowerCase());
    });

    it("handles input without 0x prefix", () => {
      const noPrefix = EXPECTED_BYTES32.slice(2);
      expect(bytes32ToUuid(noPrefix)).toBe(VALID_UUID.toLowerCase());
    });

    it("throws on wrong length", () => {
      expect(() => bytes32ToUuid("0xABCD")).toThrow(
        "Invalid bytes32 hex length",
      );
    });
  });

  describe("round-trip", () => {
    it("uuid → bytes32 → uuid is identity", () => {
      const result = bytes32ToUuid(uuidToBytes32(VALID_UUID));
      expect(result).toBe(VALID_UUID.toLowerCase());
    });
  });
});

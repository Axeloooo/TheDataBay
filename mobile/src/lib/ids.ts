const UUID_REGEX =
  /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;
const BYTES32_HEX_REGEX = /^(0x)?[0-9a-fA-F]{64}$/;

export function uuidToBytes32(uuid: string): string {
  if (!UUID_REGEX.test(uuid)) {
    throw new Error("Invalid UUID format");
  }
  const hex = uuid.replace(/-/g, "").toLowerCase();
  return `0x${hex}00000000000000000000000000000000`;
}

export function bytes32ToUuid(bytes32Hex: string): string {
  if (!BYTES32_HEX_REGEX.test(bytes32Hex)) {
    throw new Error("Invalid bytes32 hex format");
  }

  const normalized = bytes32Hex.startsWith("0x")
    ? bytes32Hex.slice(2)
    : bytes32Hex;

  const normalizedHex = normalized.toLowerCase();
  const uuidHex = normalizedHex.slice(0, 32);
  return `${uuidHex.slice(0, 8)}-${uuidHex.slice(8, 12)}-${uuidHex.slice(12, 16)}-${uuidHex.slice(16, 20)}-${uuidHex.slice(20)}`;
}

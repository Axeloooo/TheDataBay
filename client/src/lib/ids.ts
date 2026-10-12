const UUID_REGEX =
  /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;

export function uuidToBytes32(uuid: string): string {
  if (!UUID_REGEX.test(uuid)) {
    throw new Error("Invalid UUID format");
  }
  const hex = uuid.replace(/-/g, "").toLowerCase();
  return `0x${hex}00000000000000000000000000000000`;
}

export function bytes32ToUuid(bytes32Hex: string): string {
  const normalized = bytes32Hex.startsWith("0x")
    ? bytes32Hex.slice(2)
    : bytes32Hex;
  if (normalized.length !== 64) {
    throw new Error("Invalid bytes32 hex length");
  }
  const uuidHex = normalized.slice(0, 32);
  return `${uuidHex.slice(0, 8)}-${uuidHex.slice(8, 12)}-${uuidHex.slice(12, 16)}-${uuidHex.slice(16, 20)}-${uuidHex.slice(20)}`;
}

export type NormalizeAtomicMode = "strict" | "lenient";

type NormalizeAtomicOptions = {
  mode?: NormalizeAtomicMode;
  allowBigInt?: boolean;
};

function normalizeAtomicValue(
  value: unknown,
  { allowBigInt = true }: NormalizeAtomicOptions = {},
): string {
  if (typeof value === "bigint") {
    if (!allowBigInt) {
      throw new Error("Unsupported atomic amount type.");
    }
    if (value < 0n) {
      throw new Error("Invalid atomic amount: negative bigint.");
    }
    return value.toString();
  }

  if (typeof value === "number") {
    if (
      !Number.isFinite(value) ||
      !Number.isInteger(value) ||
      value < 0 ||
      !Number.isSafeInteger(value)
    ) {
      throw new Error("Invalid atomic amount: non-integer or unsafe number.");
    }
    return value.toString();
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!/^\d+$/.test(trimmed)) {
      throw new Error("Invalid atomic amount: non-numeric string.");
    }
    return trimmed;
  }

  throw new Error("Unsupported atomic amount type.");
}

export function normalizeAtomicString(
  value: unknown,
  options: NormalizeAtomicOptions = {},
): string {
  const mode = options.mode ?? "strict";
  if (mode === "strict") {
    return normalizeAtomicValue(value, options);
  }

  try {
    return normalizeAtomicValue(value, options);
  } catch {
    return "0";
  }
}

import type { StorageValue } from "zustand/middleware";

export function ensurePersistFormat<T>(
  key: string,
  mapLegacyRawToState: (raw: string) => T,
): void {
  if (typeof window === "undefined") return;

  const raw = window.localStorage.getItem(key);
  if (!raw) return;

  try {
    const parsed = JSON.parse(raw) as StorageValue<T>;
    if (parsed && typeof parsed === "object" && "state" in parsed) {
      return;
    }
  } catch {
    // Legacy value; convert below.
  }

  const wrapped: StorageValue<T> = {
    state: mapLegacyRawToState(raw),
    version: 0,
  };
  window.localStorage.setItem(key, JSON.stringify(wrapped));
}

export function safeJsonParse<T>(value: string): T | null {
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
}

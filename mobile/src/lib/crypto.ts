/**
 * Cryptography utilities for AES-GCM decryption.
 *
 * Uses the Web Crypto API (`crypto.subtle`) available in React Native's
 * Hermes engine on Expo SDK 53+.
 *
 * If `crypto.subtle` is unavailable on a target device, replace the body
 * of `decryptAesGcm` with `react-native-quick-crypto` bindings:
 *   import { createDecipheriv } from 'react-native-quick-crypto';
 */

export function decodeBase64(input: string): Uint8Array {
  const normalized = input.replace(/\s/g, "");
  // atob is available on React Native (Hermes)
  const binary = atob(normalized);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function uint8ToArrayBuffer(bytes: Uint8Array): ArrayBuffer {
  return bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength,
  ) as ArrayBuffer;
}

export async function importAesKey(keyBytes: Uint8Array): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    uint8ToArrayBuffer(keyBytes),
    { name: "AES-GCM" },
    false,
    ["decrypt"],
  );
}

export async function decryptAesGcm(params: {
  ciphertext: ArrayBuffer;
  key: Uint8Array;
  nonce: Uint8Array;
  aad?: Uint8Array;
}): Promise<ArrayBuffer> {
  const cryptoKey = await importAesKey(params.key);
  return crypto.subtle.decrypt(
    {
      name: "AES-GCM",
      iv: uint8ToArrayBuffer(params.nonce),
      additionalData: params.aad ? uint8ToArrayBuffer(params.aad) : undefined,
    },
    cryptoKey,
    params.ciphertext,
  );
}

export function utf8Bytes(text: string): Uint8Array {
  return new TextEncoder().encode(text);
}

import AsyncStorage from "@react-native-async-storage/async-storage";

export type PersistedUploadSession = {
  jobId: string;
  listingId: string | null;
  title: string;
  description: string;
  seller: string;
  price_atomic: string;
  settlement_currency: "USDC";
  settlement_decimals: 6;
  fileName?: string;
  status?: "queued" | "running" | "completed" | "failed";
  datasetUrl?: string;
  datasetHash?: string;
  signatureUrl?: string;
  signatureHash?: string;
  error?: string;
  createdAt: string;
  updatedAt: string;
  createTxHash?: string;
  priceWei?: string;
};

const STORAGE_KEY = "thedatabay_upload_session_v1";

export async function loadUploadSession() {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as PersistedUploadSession) : null;
  } catch {
    return null;
  }
}

export async function saveUploadSession(session: PersistedUploadSession) {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export async function clearUploadSession() {
  await AsyncStorage.removeItem(STORAGE_KEY);
}

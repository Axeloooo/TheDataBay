export type PersistedUploadSession = {
  /** Legacy job id from pre-synchronous uploads. */
  jobId?: string;
  listingId: string | null;
  title: string;
  description: string;
  seller: string;
  priceAtomic?: string;
  settlementCurrency?: "USDC" | "CADC";
  settlementDecimals?: number;
  /** Legacy compatibility for pre-migration drafts. */
  priceWei?: string;
  fileName?: string;
  status?: "queued" | "running" | "completed" | "failed";
  datasetUrl?: string;
  datasetHash?: string;
  preview?: { column_names: string[]; rows: string[][] };
  stats?: {
    total_rows: number;
    total_columns: number;
    has_header: boolean;
    empty_rows_skipped: number;
  };
  vectorSpec?: { model: string; dimension: number };
  signatureUrl?: string;
  signatureHash?: string;
  error?: string;
  createdAt: string;
  updatedAt: string;
  createTxHash?: string;
  toastNotifiedStatus?: "completed" | "failed" | null;
};

const STORAGE_KEY = "thedatabay_upload_session_v1";

export function loadUploadSession(): PersistedUploadSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as PersistedUploadSession;
  } catch {
    return null;
  }
}

export function saveUploadSession(session: PersistedUploadSession): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearUploadSession(): void {
  localStorage.removeItem(STORAGE_KEY);
}

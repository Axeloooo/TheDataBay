import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { toast } from "sonner";
import { backend } from "@/lib/backend";
import { createItemTx } from "@/lib/marketplace";
import { uuidToBytes32 } from "@/lib/ids";
import { fireConfettiBurst } from "@/lib/confetti";
import type { DisplayCurrency } from "@/lib/fx";
import { parseUnits } from "ethers";
import type { JobResponse, JobStatusResponse } from "@/types/llm";
import {
  clearUploadSession,
  loadUploadSession,
  saveUploadSession,
  type PersistedUploadSession,
} from "@/lib/upload-session";

type UploadStatus = "queued" | "running" | "completed" | "failed";

type UploadStore = {
  title: string;
  description: string;
  priceUsdc: string;
  displayCurrency: DisplayCurrency;
  file: File | null;
  job: JobResponse | null;
  jobStatus: JobStatusResponse | null;
  loading: boolean;
  error: string | null;
  createTxHash: string | null;
  isCreating: boolean;
  persistedSession: PersistedUploadSession | null;
  pollTimerId: number | null;
  hasInitialized: boolean;
  setTitle: (value: string) => void;
  setDescription: (value: string) => void;
  setPriceUsdc: (value: string) => void;
  setDisplayCurrency: (value: DisplayCurrency) => void;
  setFile: (value: File | null) => void;
  setError: (value: string | null) => void;
  initializeUploadState: (preferredCurrency: DisplayCurrency) => void;
  submitUpload: (address: string | null) => Promise<void>;
  pollJob: (jobId: string) => Promise<boolean>;
  startPolling: () => void;
  stopPolling: () => void;
  clearPendingSession: () => void;
  createItemOnChain: (address: string | null) => Promise<string | null>;
};

const STORAGE_KEY = "bridgemart_upload_store_v1";
const SETTLEMENT_DECIMALS = 6;

function parsePriceAtomic(priceUsdc: string): string | null {
  if (!priceUsdc) return null;
  try {
    return parseUnits(priceUsdc, SETTLEMENT_DECIMALS).toString();
  } catch {
    return null;
  }
}

function statusToUploadStatus(status: string | null | undefined): UploadStatus {
  if (status === "completed") return "completed";
  if (status === "failed") return "failed";
  if (status === "running") return "running";
  return "queued";
}

function syncSessionFromStatus(
  status: JobStatusResponse,
  current: PersistedUploadSession,
): PersistedUploadSession {
  const updated: PersistedUploadSession = {
    ...current,
    listingId: status.listing_id ?? current.listingId,
    status: statusToUploadStatus(status.status),
    datasetUrl: status.dataset_url ?? current.datasetUrl,
    datasetHash: status.dataset_hash ?? current.datasetHash,
    signatureUrl: status.signature?.signature_url ?? current.signatureUrl,
    signatureHash: status.signature?.signature_hash ?? current.signatureHash,
    error: status.error ?? current.error,
    updatedAt: new Date().toISOString(),
  };
  saveUploadSession(updated);
  return updated;
}

function maybeNotifyTerminalStatus(
  session: PersistedUploadSession,
  status: JobStatusResponse,
) {
  const terminal = status.status === "completed" || status.status === "failed";
  if (!terminal) return session;
  if (session.toastNotifiedStatus === status.status) return session;

  if (status.status === "completed") {
    toast.success("Embedding job completed", {
      description:
        "Dataset encrypted and uploaded. Ready to sign on-chain listing.",
    });
  } else {
    toast.error("Embedding job failed", {
      description: status.error ?? "Review the error details and retry.",
    });
  }

  const updated: PersistedUploadSession = {
    ...session,
    toastNotifiedStatus: status.status === "completed" ? "completed" : "failed",
    updatedAt: new Date().toISOString(),
  };
  saveUploadSession(updated);
  return updated;
}

export const useUploadStore = create<UploadStore>()(
  persist(
    (set, get) => ({
      title: "",
      description: "",
      priceUsdc: "",
      displayCurrency: "USDC",
      file: null,
      job: null,
      jobStatus: null,
      loading: false,
      error: null,
      createTxHash: null,
      isCreating: false,
      persistedSession: null,
      pollTimerId: null,
      hasInitialized: false,
      setTitle: (value) => set({ title: value }),
      setDescription: (value) => set({ description: value }),
      setPriceUsdc: (value) => set({ priceUsdc: value }),
      setDisplayCurrency: (value) => set({ displayCurrency: value }),
      setFile: (value) => set({ file: value }),
      setError: (value) => set({ error: value }),
      initializeUploadState: (preferredCurrency) => {
        const state = get();
        if (state.hasInitialized) return;

        const session = loadUploadSession();
        const legacyState = state as UploadStore & {
          priceEth?: string;
          payCurrency?: DisplayCurrency;
        };
        const nextState: Partial<UploadStore> = {
          hasInitialized: true,
        };
        const hasDraft =
          !!state.title ||
          !!state.description ||
          !!legacyState.priceUsdc ||
          !!legacyState.priceEth ||
          legacyState.displayCurrency !== "USDC" ||
          legacyState.payCurrency !== undefined;
        if (!hasDraft && !session) {
          nextState.displayCurrency = preferredCurrency;
        }

        if (!session) {
          set(nextState);
          return;
        }

        nextState.persistedSession = session;
        if (!state.title) {
          nextState.title = session.title;
        }
        if (!state.description) {
          nextState.description = session.description;
        }
        const sessionPriceAtomic = session.priceAtomic ?? session.priceWei;
        if (!legacyState.priceUsdc && sessionPriceAtomic) {
          const whole = BigInt(sessionPriceAtomic) / 10n ** BigInt(SETTLEMENT_DECIMALS);
          const fraction = (BigInt(sessionPriceAtomic) % 10n ** BigInt(SETTLEMENT_DECIMALS))
            .toString()
            .padStart(SETTLEMENT_DECIMALS, "0");
          nextState.priceUsdc = `${whole}.${fraction}`.replace(/\.?0+$/, "");
        }
        if (!hasDraft) {
          nextState.displayCurrency = preferredCurrency;
        } else if (legacyState.payCurrency) {
          nextState.displayCurrency = legacyState.payCurrency;
        }
        if (session.jobId && !state.job) {
          nextState.job = {
            job_id: session.jobId,
            listing_id: session.listingId ?? "",
            status: session.status ?? "queued",
          };
        }
        if (
          session.listingId &&
          session.status &&
          (session.status === "completed" || session.status === "failed") &&
          !state.jobStatus
        ) {
          nextState.jobStatus = {
            job_id: session.jobId,
            status: session.status,
            listing_id: session.listingId,
            created_at: session.createdAt,
            started_at: null,
            completed_at: null,
            filename: session.fileName ?? "dataset.csv",
            error: session.error,
            dataset_url: session.datasetUrl,
            dataset_hash: session.datasetHash,
            signature:
              session.signatureUrl && session.signatureHash
                ? {
                    signature_url: session.signatureUrl,
                    signature_hash: session.signatureHash,
                  }
                : undefined,
          };
        }

        set(nextState);
      },
      submitUpload: async (address) => {
        const state = get();

        if (!address) {
          set({ error: "Connect wallet to continue." });
          return;
        }
        if (!state.file) {
          set({ error: "Select a dataset file." });
          return;
        }
        const legacyState = state as UploadStore & {
          priceEth?: string;
        };
        const priceAtomic = parsePriceAtomic(
          legacyState.priceUsdc ?? legacyState.priceEth ?? "",
        );
        if (!priceAtomic) {
          set({ error: "Enter a valid price." });
          return;
        }

        const formData = new FormData();
        formData.append("file", state.file);
        formData.append("title", state.title);
        formData.append("description", state.description);
        formData.append("seller", address);
        formData.append("price_atomic", priceAtomic);
        formData.append("settlement_currency", "USDC");
        formData.append("settlement_decimals", String(SETTLEMENT_DECIMALS));
        // Legacy compatibility while the backend finishes the migration.
        formData.append("price", priceAtomic);
        formData.append("seller_wallet_type", "evm");

        set({ loading: true, error: null });

        try {
          const response = await backend.submitEmbedBatch(formData);
          const nextSession: PersistedUploadSession = {
            jobId: response.job_id,
            listingId: response.listing_id ?? null,
            title: state.title,
            description: state.description,
            seller: address,
            priceAtomic,
            settlementCurrency: "USDC",
            settlementDecimals: SETTLEMENT_DECIMALS,
            fileName: state.file.name,
            status: "queued",
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            toastNotifiedStatus: null,
          };

          saveUploadSession(nextSession);
          set({
            job: response,
            persistedSession: nextSession,
            loading: true,
          });

          const keepPolling = await get().pollJob(response.job_id);
          if (keepPolling) {
            get().startPolling();
          }
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : "Upload failed",
            loading: false,
          });
        }
      },
      pollJob: async (jobId) => {
        try {
          const status = await backend.getJobStatus(jobId);
          let session = get().persistedSession;

          if (!session) {
            session = loadUploadSession();
          }

          if (session && session.jobId === jobId) {
            const synced = syncSessionFromStatus(status, session);
            const notified = maybeNotifyTerminalStatus(synced, status);
            set({ persistedSession: notified });
          }

          set({ jobStatus: status });

          if (status.status === "completed" || status.status === "failed") {
            get().stopPolling();
            set({ loading: false });
            return false;
          }

          return true;
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to fetch job status";
          if (message.toLowerCase().includes("job not found")) {
            set({
              error:
                "Session found, but job is no longer available on server memory. If upload already completed, you can still sign if required fields are present.",
              loading: false,
            });
            return false;
          }

          set({ error: message, loading: false });
          return false;
        }
      },
      startPolling: () => {
        const state = get();
        const activeJobId = state.job?.job_id ?? state.persistedSession?.jobId;
        const activeStatus =
          state.jobStatus?.status ?? state.persistedSession?.status;

        if (!activeJobId) return;
        if (activeStatus === "completed" || activeStatus === "failed") return;

        get().stopPolling();
        set({ loading: true });

        void get().pollJob(activeJobId);
        const intervalId = window.setInterval(() => {
          void get().pollJob(activeJobId);
        }, 8000);

        set({ pollTimerId: intervalId });
      },
      stopPolling: () => {
        const intervalId = get().pollTimerId;
        if (intervalId === null) return;
        window.clearInterval(intervalId);
        set({ pollTimerId: null });
      },
      clearPendingSession: () => {
        clearUploadSession();
        get().stopPolling();
        set({
          persistedSession: null,
          job: null,
          jobStatus: null,
          createTxHash: null,
          error: null,
          loading: false,
        });
      },
      createItemOnChain: async (address) => {
        const state = get();
        const currentListingId =
          state.jobStatus?.listing_id ??
          state.persistedSession?.listingId ??
          null;
        const currentDatasetUrl =
          state.jobStatus?.dataset_url ?? state.persistedSession?.datasetUrl;
        const currentDatasetHash =
          state.jobStatus?.dataset_hash ?? state.persistedSession?.datasetHash;
        const currentSignatureUrl =
          state.jobStatus?.signature?.signature_url ??
          state.persistedSession?.signatureUrl;
        const currentSignatureHash =
          state.jobStatus?.signature?.signature_hash ??
          state.persistedSession?.signatureHash;

        if (!address) {
          set({ error: "Connect wallet to create item." });
          return null;
        }
        if (!currentListingId || !currentDatasetUrl || !currentDatasetHash) {
          set({ error: "Missing dataset upload outputs." });
          return null;
        }
        if (!currentSignatureUrl || !currentSignatureHash) {
          set({ error: "Missing signature upload outputs." });
          return null;
        }

        const effectivePriceAtomic =
          state.persistedSession?.priceAtomic ??
          state.persistedSession?.priceWei ??
          parsePriceAtomic(state.priceUsdc);
        if (!effectivePriceAtomic) {
          set({ error: "Missing price." });
          return null;
        }

        set({ isCreating: true, error: null });

        try {
          const txHash = await createItemTx({
            listingId: currentListingId,
            title: state.persistedSession?.title ?? state.title,
            description:
              state.persistedSession?.description ?? state.description,
            seller: address,
            priceAtomic: effectivePriceAtomic,
            datasetUrl: currentDatasetUrl,
            datasetHash: currentDatasetHash,
            signatureUrl: currentSignatureUrl,
            signatureHash: currentSignatureHash,
          });

          toast.success("Listing created on-chain", { description: txHash });
          fireConfettiBurst();
          clearUploadSession();

          set({
            createTxHash: txHash,
            persistedSession: null,
            job: null,
            jobStatus: null,
            isCreating: false,
          });

          return uuidToBytes32(currentListingId);
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : "Failed to create item",
            isCreating: false,
          });
          return null;
        }
      },
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        title: state.title,
        description: state.description,
        priceUsdc: state.priceUsdc,
        displayCurrency: state.displayCurrency,
        job: state.job,
        jobStatus: state.jobStatus,
        persistedSession: state.persistedSession,
        createTxHash: state.createTxHash,
      }),
      onRehydrateStorage: () => (state) => {
        if (!state) return;
        state.file = null;
        state.loading = false;
        state.isCreating = false;
        state.error = null;
        state.pollTimerId = null;
      },
    },
  ),
);

export function selectUploadPriceAtomic(priceUsdc: string): string | null {
  return parsePriceAtomic(priceUsdc);
}

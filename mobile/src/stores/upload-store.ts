import type { DocumentPickerAsset } from "expo-document-picker";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import { backend } from "@/src/lib/backend";
import { type DisplayCurrency } from "@/src/lib/fx";
import {
  SETTLEMENT_CURRENCY,
  SETTLEMENT_DECIMALS,
  formatSettlementAmount,
  getUsdcTokenAddress,
  parseSettlementAmount,
  createItemTx,
} from "@/src/lib/marketplace";
import {
  clearUploadSession,
  loadUploadSession,
  saveUploadSession,
  type PersistedUploadSession,
} from "@/src/lib/upload-session";
import type { JobResponse, JobStatusResponse } from "@/src/types/llm";

type UploadStatus = "queued" | "running" | "completed" | "failed";

type UploadStore = {
  title: string;
  description: string;
  settlementAmount: string;
  quoteCurrency: DisplayCurrency;
  selectedFile: DocumentPickerAsset | null;
  job: JobResponse | null;
  jobStatus: JobStatusResponse | null;
  loading: boolean;
  error: string | null;
  isCreating: boolean;
  createTxHash: string | null;
  persistedSession: PersistedUploadSession | null;
  pollTimerId: ReturnType<typeof setInterval> | null;
  hasInitialized: boolean;
  setTitle: (value: string) => void;
  setDescription: (value: string) => void;
  setSettlementAmount: (value: string) => void;
  setQuoteCurrency: (value: DisplayCurrency) => void;
  setSelectedFile: (value: DocumentPickerAsset | null) => void;
  setError: (value: string | null) => void;
  initializeUploadState: (displayCurrency: DisplayCurrency) => Promise<void>;
  submitUpload: (address: string | null) => Promise<void>;
  pollJob: (jobId: string) => Promise<boolean>;
  startPolling: () => void;
  stopPolling: () => void;
  clearPendingSession: () => Promise<void>;
  createListingOnChain: (address: string | null) => Promise<string | null>;
};

const STORAGE_KEY = "thedatabay_upload_store_v1";
const ZERO_BYTES32 = `0x${"0".repeat(64)}`;

function statusToUploadStatus(status: string | null | undefined): UploadStatus {
  if (status === "completed") return "completed";
  if (status === "failed") return "failed";
  if (status === "running") return "running";
  return "queued";
}

async function syncSessionFromStatus(
  status: JobStatusResponse,
  current: PersistedUploadSession,
) {
  const updated: PersistedUploadSession = {
    ...current,
    listingId: status.listing_id ?? current.listingId,
    status: statusToUploadStatus(status.status),
    datasetUrl: status.dataset_url ?? current.datasetUrl,
    datasetHash: status.dataset_hash ?? current.datasetHash,
    error: status.error ?? current.error,
    updatedAt: new Date().toISOString(),
  };
  await saveUploadSession(updated);
  return updated;
}

export const useUploadStore = create<UploadStore>()(
  persist(
    (set, get) => ({
      title: "",
      description: "",
      settlementAmount: "",
      quoteCurrency: "USDC",
      selectedFile: null,
      job: null,
      jobStatus: null,
      loading: false,
      error: null,
      isCreating: false,
      createTxHash: null,
      persistedSession: null,
      pollTimerId: null,
      hasInitialized: false,

      setTitle: (value) => set({ title: value }),
      setDescription: (value) => set({ description: value }),
      setSettlementAmount: (value) => set({ settlementAmount: value }),
      setQuoteCurrency: (value) => set({ quoteCurrency: value }),
      setSelectedFile: (value) => set({ selectedFile: value }),
      setError: (value) => set({ error: value }),

      async initializeUploadState(displayCurrency) {
        const state = get();
        if (state.hasInitialized) {
          return;
        }

        const session = await loadUploadSession();
        const nextState: Partial<UploadStore> = { hasInitialized: true };
        const hasDraft =
          !!state.title ||
          !!state.description ||
          !!state.settlementAmount ||
          state.quoteCurrency !== "USDC";

        if (!hasDraft) {
          nextState.quoteCurrency = displayCurrency;
        }

        if (!session) {
          set(nextState);
          return;
        }

        nextState.persistedSession = session;
        if (!state.title) nextState.title = session.title;
        if (!state.description) nextState.description = session.description;
        if (!state.settlementAmount) {
          if (session.price_atomic) {
            nextState.settlementAmount = formatSettlementAmount(
              session.price_atomic,
              session.settlement_decimals ?? SETTLEMENT_DECIMALS,
            );
          } else if (session.priceWei) {
            nextState.settlementAmount = formatSettlementAmount(
              session.priceWei,
              18,
            );
          }
        }
        if (session.jobId && !state.job) {
          nextState.job = {
            job_id: session.jobId,
            listing_id: session.listingId ?? "",
            status: session.status ?? "queued",
          };
        }

        set(nextState);
      },

      async submitUpload(address) {
        const state = get();

        if (!address) {
          set({ error: "Connect a wallet to continue." });
          return;
        }
        if (!state.selectedFile) {
          set({ error: "Select a CSV dataset file." });
          return;
        }
        const priceAtomic = parseSettlementAmount(
          state.settlementAmount,
          SETTLEMENT_DECIMALS,
        );
        if (!priceAtomic) {
          set({ error: "Enter a valid USDC settlement amount." });
          return;
        }

        const formData = new FormData();
        formData.append("file", {
          uri: state.selectedFile.uri,
          name: state.selectedFile.name,
          type: state.selectedFile.mimeType ?? "text/csv",
        } as never);
        formData.append("title", state.title);
        formData.append("description", state.description);
        formData.append("seller", address);
        formData.append("price_atomic", priceAtomic);
        formData.append("settlement_currency", SETTLEMENT_CURRENCY);
        formData.append("settlement_decimals", String(SETTLEMENT_DECIMALS));
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
            price_atomic: priceAtomic,
            settlement_currency: SETTLEMENT_CURRENCY,
            settlement_decimals: SETTLEMENT_DECIMALS,
            fileName: state.selectedFile.name,
            status: "queued",
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          };

          await saveUploadSession(nextSession);
          set({
            job: response,
            persistedSession: nextSession,
            loading: true,
          });

          const keepPolling = await get().pollJob(response.job_id);
          if (keepPolling) {
            get().startPolling();
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Upload failed.",
            loading: false,
          });
        }
      },

      async pollJob(jobId) {
        try {
          const status = await backend.getJobStatus(jobId);
          const session = get().persistedSession ?? (await loadUploadSession());

          if (session && session.jobId === jobId) {
            const synced = await syncSessionFromStatus(status, session);
            set({ persistedSession: synced });
          }

          set({ jobStatus: status });

          if (status.status === "completed" || status.status === "failed") {
            get().stopPolling();
            set({ loading: false });
            return false;
          }

          return true;
        } catch (error) {
          get().stopPolling();
          set({
            error:
              error instanceof Error
                ? error.message
                : "Failed to fetch upload status.",
            loading: false,
          });
          return false;
        }
      },

      startPolling() {
        const state = get();
        const activeJobId = state.job?.job_id ?? state.persistedSession?.jobId;
        const activeStatus =
          state.jobStatus?.status ?? state.persistedSession?.status;

        if (!activeJobId) {
          return;
        }
        if (activeStatus === "completed" || activeStatus === "failed") {
          return;
        }

        get().stopPolling();
        set({ loading: true });

        void get().pollJob(activeJobId);
        const intervalId = setInterval(() => {
          void get().pollJob(activeJobId);
        }, 8000);

        set({ pollTimerId: intervalId });
      },

      stopPolling() {
        const intervalId = get().pollTimerId;
        if (intervalId !== null) {
          clearInterval(intervalId);
        }
        set({ pollTimerId: null });
      },

      async clearPendingSession() {
        await clearUploadSession();
        get().stopPolling();
        set({
          persistedSession: null,
          job: null,
          jobStatus: null,
          createTxHash: null,
          error: null,
          loading: false,
          selectedFile: null,
        });
      },

      async createListingOnChain(address) {
        const state = get();
        const currentListingId =
          state.jobStatus?.listing_id ??
          state.persistedSession?.listingId ??
          null;
        const currentDatasetUrl =
          state.jobStatus?.dataset_url ?? state.persistedSession?.datasetUrl;
        const currentDatasetHash =
          state.jobStatus?.dataset_hash ?? state.persistedSession?.datasetHash;

        if (!address) {
          set({ error: "Connect the seller wallet to create the listing." });
          return null;
        }
        if (!currentListingId || !currentDatasetUrl || !currentDatasetHash) {
          set({ error: "Missing uploaded dataset outputs." });
          return null;
        }

        const effectivePriceAtomic =
          state.persistedSession?.price_atomic ??
          parseSettlementAmount(state.settlementAmount, SETTLEMENT_DECIMALS);
        if (!effectivePriceAtomic) {
          set({ error: "Missing settlement amount." });
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
            paymentToken: getUsdcTokenAddress(),
            priceAtomic: effectivePriceAtomic,
            datasetUrl: currentDatasetUrl,
            datasetHash: currentDatasetHash,
            signatureUrl: "",
            signatureHash: ZERO_BYTES32,
          });

          await clearUploadSession();

          set({
            createTxHash: txHash,
            persistedSession: null,
            job: null,
            jobStatus: null,
            isCreating: false,
            selectedFile: null,
          });

          return currentListingId;
        } catch (error) {
          set({
            error:
              error instanceof Error
                ? error.message
                : "Failed to create listing.",
            isCreating: false,
          });
          return null;
        }
      },
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({
        title: state.title,
        description: state.description,
        settlementAmount: state.settlementAmount,
        quoteCurrency: state.quoteCurrency,
        job: state.job,
        jobStatus: state.jobStatus,
        persistedSession: state.persistedSession,
        createTxHash: state.createTxHash,
      }),
      onRehydrateStorage: () => (state) => {
        if (!state) return;
        state.selectedFile = null;
        state.loading = false;
        state.isCreating = false;
        state.error = null;
        state.pollTimerId = null;
      },
    },
  ),
);

export function selectUploadPriceAtomic(settlementAmount: string) {
  return parseSettlementAmount(settlementAmount, SETTLEMENT_DECIMALS);
}

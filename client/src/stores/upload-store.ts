import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { toast } from "sonner";
import { parseUnits } from "ethers";
import { backend } from "@/lib/backend";
import {
  createItemTx,
  getPaymentTokenAddressForCurrency,
} from "@/lib/marketplace";
import { uuidToBytes32 } from "@/lib/ids";
import { fireConfettiBurst } from "@/lib/confetti";
import type { DisplayCurrency } from "@/lib/fx";
import { SETTLEMENT_TOKENS, type SettlementCurrency } from "@/types/contract";
import type { DatasetEmbedResponse } from "@/types/dataset";
import {
  clearUploadSession,
  loadUploadSession,
  saveUploadSession,
  type PersistedUploadSession,
} from "@/lib/upload-session";
import { walletRuntime } from "@/lib/wallet/runtime";

type UploadStore = {
  title: string;
  description: string;
  priceUsdc: string;
  settlementCurrency: SettlementCurrency;
  displayCurrency: DisplayCurrency;
  file: File | null;
  embedResult: DatasetEmbedResponse | null;
  loading: boolean;
  error: string | null;
  createTxHash: string | null;
  isCreating: boolean;
  persistedSession: PersistedUploadSession | null;
  hasInitialized: boolean;
  setTitle: (value: string) => void;
  setDescription: (value: string) => void;
  setPriceUsdc: (value: string) => void;
  setSettlementCurrency: (value: SettlementCurrency) => void;
  setDisplayCurrency: (value: DisplayCurrency) => void;
  setFile: (value: File | null) => void;
  setError: (value: string | null) => void;
  initializeUploadState: (preferredCurrency: DisplayCurrency) => void;
  submitUpload: (address: string | null) => Promise<void>;
  clearPendingSession: () => void;
  createItemOnChain: (address: string | null) => Promise<string | null>;
};

const STORAGE_KEY = "thedatabay_upload_store_v3";
const ZERO_BYTES32 = `0x${"0".repeat(64)}`;

function settlementDecimalsFor(currency: SettlementCurrency): number {
  return SETTLEMENT_TOKENS[currency].decimals;
}

function parsePriceAtomic(
  priceStr: string,
  currency: SettlementCurrency = "USDC",
): string | null {
  if (!priceStr) return null;
  try {
    return parseUnits(priceStr, settlementDecimalsFor(currency)).toString();
  } catch {
    return null;
  }
}

function sessionFromResult(
  response: DatasetEmbedResponse,
  state: UploadStore,
  seller: string,
  priceAtomic: string,
): PersistedUploadSession {
  return {
    listingId: response.listing_id,
    title: state.title,
    description: state.description,
    seller,
    priceAtomic,
    settlementCurrency: state.settlementCurrency,
    settlementDecimals: settlementDecimalsFor(state.settlementCurrency),
    fileName: state.file?.name,
    status: "completed",
    datasetUrl: response.dataset_url,
    datasetHash: response.dataset_hash,
    preview: response.preview,
    stats: response.stats,
    vectorSpec: response.vector_spec,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    toastNotifiedStatus: "completed",
  };
}

export const useUploadStore = create<UploadStore>()(
  persist(
    (set, get) => ({
      title: "",
      description: "",
      priceUsdc: "",
      settlementCurrency: "USDC",
      displayCurrency: "USDC",
      file: null,
      embedResult: null,
      loading: false,
      error: null,
      createTxHash: null,
      isCreating: false,
      persistedSession: null,
      hasInitialized: false,
      setTitle: (value) => set({ title: value }),
      setDescription: (value) => set({ description: value }),
      setPriceUsdc: (value) => set({ priceUsdc: value }),
      setSettlementCurrency: (value) => set({ settlementCurrency: value }),
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
        const nextState: Partial<UploadStore> = { hasInitialized: true };
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
        if (!state.title) nextState.title = session.title;
        if (!state.description) nextState.description = session.description;
        if (!legacyState.priceUsdc && session.priceAtomic) {
          const sessionCurrency: SettlementCurrency =
            session.settlementCurrency === "CADC" ? "CADC" : "USDC";
          const sessionDecimals = settlementDecimalsFor(sessionCurrency);
          const whole =
            BigInt(session.priceAtomic) / 10n ** BigInt(sessionDecimals);
          const fraction = (
            BigInt(session.priceAtomic) %
            10n ** BigInt(sessionDecimals)
          )
            .toString()
            .padStart(sessionDecimals, "0");
          nextState.priceUsdc = `${whole}.${fraction}`.replace(/\.?0+$/, "");
          nextState.settlementCurrency = sessionCurrency;
        }
        if (!hasDraft) {
          nextState.displayCurrency = preferredCurrency;
        } else if (legacyState.payCurrency) {
          nextState.displayCurrency = legacyState.payCurrency;
        }
        if (session.listingId && session.datasetUrl && session.datasetHash) {
          nextState.embedResult = {
            listing_id: session.listingId,
            dataset_url: session.datasetUrl,
            dataset_hash: session.datasetHash,
            preview: session.preview ?? { column_names: [], rows: [] },
            stats: session.stats ?? {
              total_rows: 0,
              total_columns: 0,
              has_header: false,
              empty_rows_skipped: 0,
            },
            vector_spec: session.vectorSpec ?? {
              model: "nomic-embed-text",
              dimension: 768,
            },
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
        const legacyState = state as UploadStore & { priceEth?: string };
        if (legacyState.priceEth && !legacyState.priceUsdc) {
          set({
            error:
              "Price format has changed. Please re-enter the price in USDC to continue.",
          });
          return;
        }
        const priceAtomic = parsePriceAtomic(
          legacyState.priceUsdc ?? "",
          state.settlementCurrency,
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
        formData.append("settlement_currency", state.settlementCurrency);
        formData.append(
          "settlement_decimals",
          String(settlementDecimalsFor(state.settlementCurrency)),
        );
        formData.append("seller_wallet_type", "evm");

        set({ loading: true, error: null });

        try {
          const response = await backend.submitDataset(formData);
          const nextSession = sessionFromResult(
            response,
            state,
            address,
            priceAtomic,
          );
          saveUploadSession(nextSession);
          toast.success("Dataset prepared", {
            description:
              "Dataset encrypted and uploaded. Ready to sign on-chain listing.",
          });
          set({
            embedResult: response,
            persistedSession: nextSession,
            loading: false,
          });
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : "Upload failed",
            loading: false,
          });
        }
      },
      clearPendingSession: () => {
        clearUploadSession();
        set({
          persistedSession: null,
          embedResult: null,
          createTxHash: null,
          error: null,
          loading: false,
        });
      },
      createItemOnChain: async (address) => {
        const state = get();
        const currentListingId =
          state.embedResult?.listing_id ??
          state.persistedSession?.listingId ??
          null;
        const currentDatasetUrl =
          state.embedResult?.dataset_url ?? state.persistedSession?.datasetUrl;
        const currentDatasetHash =
          state.embedResult?.dataset_hash ??
          state.persistedSession?.datasetHash;

        if (!address) {
          set({ error: "Connect wallet to create item." });
          return null;
        }
        if (!currentListingId || !currentDatasetUrl || !currentDatasetHash) {
          set({ error: "Missing dataset upload outputs." });
          return null;
        }

        const parsedPriceAtomic = parsePriceAtomic(
          state.priceUsdc,
          state.settlementCurrency,
        );
        const effectivePriceAtomic =
          state.persistedSession?.priceAtomic ?? parsedPriceAtomic;

        if (
          !effectivePriceAtomic &&
          state.persistedSession?.priceWei &&
          !state.persistedSession?.priceAtomic &&
          !state.priceUsdc
        ) {
          set({
            error:
              "Saved price from an older draft is incompatible with current pricing. Please re-enter the listing price.",
          });
          return null;
        }
        if (!effectivePriceAtomic) {
          set({ error: "Missing price." });
          return null;
        }

        set({ isCreating: true, error: null });

        try {
          await walletRuntime.switchToConfiguredChain();
          const settlementCurrency =
            state.persistedSession?.settlementCurrency ??
            state.settlementCurrency;
          const txHash = await createItemTx({
            listingId: currentListingId,
            title: state.persistedSession?.title ?? state.title,
            description:
              state.persistedSession?.description ?? state.description,
            seller: address,
            paymentToken: getPaymentTokenAddressForCurrency(settlementCurrency),
            priceAtomic: effectivePriceAtomic,
            datasetUrl: currentDatasetUrl,
            datasetHash: currentDatasetHash,
            signatureUrl: "",
            signatureHash: ZERO_BYTES32,
          });

          toast.success("Listing created on-chain", { description: txHash });
          fireConfettiBurst();
          clearUploadSession();

          set({
            createTxHash: txHash,
            persistedSession: null,
            embedResult: null,
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
        settlementCurrency: state.settlementCurrency,
        displayCurrency: state.displayCurrency,
        embedResult: state.embedResult,
        persistedSession: state.persistedSession,
        createTxHash: state.createTxHash,
      }),
      onRehydrateStorage: () => (state) => {
        if (!state) return;
        state.file = null;
        state.loading = false;
        state.isCreating = false;
        state.error = null;
        if (!state.settlementCurrency) {
          state.settlementCurrency = "USDC";
        }
      },
    },
  ),
);

export function selectUploadPriceAtomic(
  priceUsdc: string,
  currency: SettlementCurrency = "USDC",
): string | null {
  return parsePriceAtomic(priceUsdc, currency);
}

import React, { useEffect, useMemo } from "react";
import * as DocumentPicker from "expo-document-picker";
import { router } from "expo-router";
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import ErrorPanel from "@/components/error-panel";
import { AppButton } from "@/components/ui/app-button";
import { StatusPill } from "@/components/ui/status-pill";
import { SurfaceCard } from "@/components/ui/surface-card";
import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";
import {
  convertSettlementToCurrency,
  formatCurrencyAmount,
  type DisplayCurrency,
} from "@/src/lib/fx";
import { SETTLEMENT_DECIMALS } from "@/src/lib/marketplace";
import { useCurrencyStore } from "@/src/stores/currency-store";
import {
  selectUploadPriceAtomic,
  useUploadStore,
} from "@/src/stores/upload-store";
import { useWalletStore } from "@/src/stores/wallet-store";

const CURRENCIES: DisplayCurrency[] = [
  "ETH",
  "USD",
  "CAD",
  "EUR",
  "MXN",
  "USDC",
  "SOL",
  "CNY",
  "USDT",
];

function FieldLabel({ label, hint }: { label: string; hint?: string }) {
  const palette = useAppTheme();

  return (
    <View style={styles.fieldLabelWrap}>
      <Text style={[styles.fieldLabel, { color: palette.text }]}>{label}</Text>
      {hint ? (
        <Text style={[styles.fieldHint, { color: palette.subtleText }]}>
          {hint}
        </Text>
      ) : null}
    </View>
  );
}

function CurrencyPicker({
  value,
  onChange,
}: {
  value: DisplayCurrency;
  onChange: (currency: DisplayCurrency) => void;
}) {
  const palette = useAppTheme();

  return (
    <View style={styles.chipWrap}>
      {CURRENCIES.map((currency) => {
        const active = currency === value;
        return (
          <Pressable
            key={currency}
            onPress={() => onChange(currency)}
            style={[
              styles.chip,
              {
                backgroundColor: active ? palette.tint : palette.cardMuted,
                borderColor: active ? palette.tint : palette.border,
              },
            ]}
          >
            <Text
              style={[
                styles.chipLabel,
                { color: active ? "#ffffff" : palette.text },
              ]}
            >
              {currency}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export default function UploadScreen() {
  const palette = useAppTheme();
  const displayCurrency = useCurrencyStore((state) => state.displayCurrency);
  const rates = useCurrencyStore((state) => state.rates);
  const {
    address,
    isConnected,
    transactionError,
    configError,
    openConnectModal,
  } = useWalletStore();
  const {
    title,
    description,
    settlementAmount,
    quoteCurrency,
    selectedFile,
    job,
    jobStatus,
    loading,
    error,
    isCreating,
    createTxHash,
    persistedSession,
    setTitle,
    setDescription,
    setSettlementAmount,
    setQuoteCurrency,
    setSelectedFile,
    initializeUploadState,
    submitUpload,
    startPolling,
    stopPolling,
    clearPendingSession,
    createListingOnChain,
  } = useUploadStore();

  useEffect(() => {
    void initializeUploadState(displayCurrency);
  }, [displayCurrency, initializeUploadState]);

  useEffect(() => {
    const activeJobId = job?.job_id ?? persistedSession?.jobId;
    const activeStatus = jobStatus?.status ?? persistedSession?.status;

    if (
      !activeJobId ||
      activeStatus === "completed" ||
      activeStatus === "failed"
    ) {
      return;
    }

    startPolling();
    return () => stopPolling();
  }, [
    job?.job_id,
    jobStatus?.status,
    persistedSession?.jobId,
    persistedSession?.status,
    startPolling,
    stopPolling,
  ]);

  const effectiveStatus = jobStatus?.status ?? persistedSession?.status ?? null;
  const currentListingId =
    jobStatus?.listing_id ?? persistedSession?.listingId ?? null;
  const currentDatasetUrl =
    jobStatus?.dataset_url ?? persistedSession?.datasetUrl ?? null;
  const priceEquivalent = useMemo(() => {
    const atomicAmount = selectUploadPriceAtomic(settlementAmount);
    if (!atomicAmount) {
      return null;
    }

    return convertSettlementToCurrency(
      atomicAmount,
      SETTLEMENT_DECIMALS,
      quoteCurrency,
      rates,
    );
  }, [quoteCurrency, rates, settlementAmount]);

  const canCreateListing =
    effectiveStatus === "completed" &&
    !!currentListingId &&
    !!address &&
    !!currentDatasetUrl;

  async function handlePickFile() {
    const result = await DocumentPicker.getDocumentAsync({
      copyToCacheDirectory: true,
      multiple: false,
      type: [
        "text/csv",
        "text/comma-separated-values",
        "public.comma-separated-values-text",
      ],
    });

    if (result.canceled) {
      return;
    }

    const asset = result.assets[0];
    if (!asset.name.toLowerCase().endsWith(".csv")) {
      Alert.alert(
        "CSV only",
        "Please choose a CSV file for the embedding pipeline.",
      );
      return;
    }

    setSelectedFile(asset);
  }

  async function handleCreateListing() {
    const listingId = await createListingOnChain(address);
    if (listingId) {
      router.push(`/dataset/${listingId}`);
    }
  }

  return (
    <SafeAreaView
      edges={["top"]}
      style={[styles.container, { backgroundColor: palette.background }]}
    >
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.hero}>
          <Text style={[styles.eyebrow, { color: palette.subtleText }]}>
            Sell datasets
          </Text>
          <Text style={[styles.title, { color: palette.text }]}>
            Upload, embed, and list from mobile
          </Text>
          <Text style={[styles.subtitle, { color: palette.subtleText }]}>
            TheDataBay mobile mirrors the web listing flow: submit your CSV,
            enter the USDC settlement amount, preview quote values, then create
            the on-chain listing with WalletConnect.
          </Text>
        </View>

        {!isConnected ? (
          <SurfaceCard style={styles.gateCard}>
            <Text style={[styles.gateTitle, { color: palette.text }]}>
              Connect the seller wallet to start
            </Text>
            <Text style={[styles.fieldHint, { color: palette.subtleText }]}>
              Uploading and listing both require the connected EVM account that
              will own the marketplace item.
            </Text>
            {configError ? <ErrorPanel message={configError} /> : null}
            {transactionError && !configError ? (
              <ErrorPanel message={transactionError} />
            ) : null}
            <AppButton
              label="Connect Wallet"
              onPress={() => void openConnectModal()}
            />
          </SurfaceCard>
        ) : null}

        {persistedSession ? (
          <SurfaceCard muted style={styles.resumeCard}>
            <View style={styles.resumeHeader}>
              <StatusPill
                label={`Resumed ${persistedSession.status ?? "queued"} session`}
                tone="warning"
              />
              <AppButton
                label="Discard"
                variant="ghost"
                onPress={() => void clearPendingSession()}
              />
            </View>
            <Text style={[styles.fieldHint, { color: palette.subtleText }]}>
              Pending listing {persistedSession.listingId ?? "not issued yet"}{" "}
              for {persistedSession.fileName ?? "dataset.csv"}.
            </Text>
          </SurfaceCard>
        ) : null}

        <SurfaceCard style={styles.sectionCard}>
          <FieldLabel label="Dataset title" />
          <TextInput
            value={title}
            onChangeText={setTitle}
            placeholder="UCI Heart Disease Dataset"
            placeholderTextColor={palette.subtleText}
            style={[
              styles.input,
              {
                backgroundColor: palette.cardMuted,
                color: palette.text,
                borderColor: palette.border,
              },
            ]}
          />

          <FieldLabel
            label="Description"
            hint="Describe coverage, quality, and likely buyer use cases."
          />
          <TextInput
            value={description}
            onChangeText={setDescription}
            placeholder="Curated CSV dataset with consistent schema and analyst-friendly metadata."
            placeholderTextColor={palette.subtleText}
            multiline
            textAlignVertical="top"
            style={[
              styles.textarea,
              {
                backgroundColor: palette.cardMuted,
                color: palette.text,
                borderColor: palette.border,
              },
            ]}
          />

          <FieldLabel label="Settlement amount (USDC)" />
          <TextInput
            value={settlementAmount}
            onChangeText={setSettlementAmount}
            placeholder="0.0500"
            placeholderTextColor={palette.subtleText}
            keyboardType="decimal-pad"
            style={[
              styles.input,
              {
                backgroundColor: palette.cardMuted,
                color: palette.text,
                borderColor: palette.border,
              },
            ]}
          />
          {priceEquivalent !== null ? (
            <Text style={[styles.fieldHint, { color: palette.subtleText }]}>
              Quote preview:{" "}
              {formatCurrencyAmount(priceEquivalent, quoteCurrency)}
            </Text>
          ) : null}

          <FieldLabel
            label="Quote currency"
            hint="Settlement is fixed to USDC; other currencies are display-only."
          />
          <CurrencyPicker value={quoteCurrency} onChange={setQuoteCurrency} />
        </SurfaceCard>

        <SurfaceCard style={styles.sectionCard}>
          <FieldLabel
            label="CSV dataset file"
            hint="Only CSV uploads are supported in this flow."
          />
          <Pressable
            onPress={() => void handlePickFile()}
            style={[
              styles.fileDrop,
              {
                borderColor: palette.border,
                backgroundColor: palette.cardMuted,
              },
            ]}
          >
            <Text style={[styles.fileTitle, { color: palette.text }]}>
              {selectedFile?.name ??
                persistedSession?.fileName ??
                "Choose a CSV file"}
            </Text>
            <Text style={[styles.fieldHint, { color: palette.subtleText }]}>
              {selectedFile?.size
                ? `${Math.max(1, Math.round(selectedFile.size / 1024))} KB`
                : "Tap to browse local files"}
            </Text>
          </Pressable>

          <AppButton
            label={loading ? "Uploading…" : "Submit for Embedding"}
            loading={loading && effectiveStatus !== "completed"}
            onPress={() => void submitUpload(address)}
            disabled={
              !isConnected ||
              !selectedFile ||
              !title ||
              !description ||
              !selectUploadPriceAtomic(settlementAmount)
            }
          />
        </SurfaceCard>

        {job || persistedSession || error || createTxHash ? (
          <SurfaceCard style={styles.sectionCard}>
            <View style={styles.statusHeader}>
              <View style={styles.statusTitleWrap}>
                <Text style={[styles.statusTitle, { color: palette.text }]}>
                  Upload status
                </Text>
                <Text style={[styles.fieldHint, { color: palette.subtleText }]}>
                  Job ID: {job?.job_id ?? persistedSession?.jobId ?? "pending"}
                </Text>
              </View>
              {effectiveStatus ? (
                <StatusPill
                  label={effectiveStatus}
                  tone={
                    effectiveStatus === "completed"
                      ? "success"
                      : effectiveStatus === "failed"
                        ? "danger"
                        : "warning"
                  }
                />
              ) : null}
            </View>

            {error ? <ErrorPanel message={error} /> : null}
            {transactionError && !error ? (
              <ErrorPanel message={transactionError} />
            ) : null}

            {currentListingId ? (
              <Text style={[styles.metaText, { color: palette.subtleText }]}>
                Listing UUID: {currentListingId}
              </Text>
            ) : null}
            {currentDatasetUrl ? (
              <Text style={[styles.metaText, { color: palette.subtleText }]}>
                Dataset URL ready for on-chain submission.
              </Text>
            ) : null}
            {createTxHash ? (
              <Text style={[styles.metaText, { color: palette.success }]}>
                Listing created on-chain: {createTxHash}
              </Text>
            ) : null}

            <AppButton
              label={
                isCreating ? "Creating Listing…" : "Create Listing On-Chain"
              }
              loading={isCreating}
              onPress={() => void handleCreateListing()}
              disabled={!canCreateListing}
            />
          </SurfaceCard>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    paddingHorizontal: AppTheme.spacing.md,
    paddingTop: AppTheme.spacing.md,
    paddingBottom: AppTheme.spacing.xxl,
    gap: AppTheme.spacing.md,
  },
  hero: {
    gap: AppTheme.spacing.sm,
    marginBottom: AppTheme.spacing.xs,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  title: {
    fontSize: 28,
    fontWeight: "800",
    lineHeight: 34,
  },
  subtitle: {
    fontSize: 15,
    lineHeight: 22,
  },
  gateCard: {
    gap: AppTheme.spacing.md,
  },
  gateTitle: {
    fontSize: 20,
    fontWeight: "800",
  },
  sectionCard: {
    gap: AppTheme.spacing.md,
  },
  fieldLabelWrap: {
    gap: 4,
  },
  fieldLabel: {
    fontSize: 15,
    fontWeight: "700",
  },
  fieldHint: {
    fontSize: 13,
    lineHeight: 20,
  },
  input: {
    minHeight: 50,
    borderWidth: 1,
    borderRadius: AppTheme.radius.md,
    paddingHorizontal: AppTheme.spacing.md,
    fontSize: 15,
    fontWeight: "500",
  },
  textarea: {
    minHeight: 120,
    borderWidth: 1,
    borderRadius: AppTheme.radius.md,
    paddingHorizontal: AppTheme.spacing.md,
    paddingVertical: AppTheme.spacing.md,
    fontSize: 15,
    fontWeight: "500",
  },
  chipWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: AppTheme.spacing.xs,
  },
  chip: {
    borderWidth: 1,
    borderRadius: AppTheme.radius.pill,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  chipLabel: {
    fontSize: 13,
    fontWeight: "700",
  },
  fileDrop: {
    borderWidth: 1,
    borderStyle: "dashed",
    borderRadius: AppTheme.radius.lg,
    padding: AppTheme.spacing.xl,
    gap: AppTheme.spacing.xs,
    alignItems: "center",
  },
  fileTitle: {
    fontSize: 16,
    fontWeight: "800",
    textAlign: "center",
  },
  statusHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: AppTheme.spacing.md,
  },
  statusTitleWrap: {
    flex: 1,
    gap: 4,
  },
  statusTitle: {
    fontSize: 18,
    fontWeight: "800",
  },
  metaText: {
    fontSize: 13,
    lineHeight: 20,
  },
  resumeCard: {
    gap: AppTheme.spacing.sm,
  },
  resumeHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: AppTheme.spacing.md,
  },
});

import React, { useCallback, useEffect, useMemo, useState } from "react";
import * as FileSystem from "expo-file-system";
import * as Sharing from "expo-sharing";
import { Stack, useLocalSearchParams } from "expo-router";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import ErrorPanel from "@/components/error-panel";
import IntegrityBadge from "@/components/integrity-badge";
import { AppButton } from "@/components/ui/app-button";
import { StatusPill } from "@/components/ui/status-pill";
import { SurfaceCard } from "@/components/ui/surface-card";
import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";
import { backend } from "@/src/lib/backend";
import { decodeBase64, decryptAesGcm, utf8Bytes } from "@/src/lib/crypto";
import { convertEthToCurrency, formatCurrencyAmount } from "@/src/lib/fx";
import { bytes32ToUuid } from "@/src/lib/ids";
import {
  verifyDatasetIntegrity,
  type IntegrityStatus,
} from "@/src/lib/integrity";
import { resolveIpfsUrl } from "@/src/lib/ipfs";
import {
  buyItemTx,
  formatPurchaseCount,
  truncateAddress,
  weiToEth,
} from "@/src/lib/marketplace";
import { useCurrencyStore } from "@/src/stores/currency-store";
import { useMarketplaceStore } from "@/src/stores/marketplace-store";
import { useWalletStore } from "@/src/stores/wallet-store";
import type { MarketplaceDataItem } from "@/src/types/contract";

type DownloadStep =
  | "idle"
  | "authorizing"
  | "fetching"
  | "decrypting"
  | "saving";

function arrayBufferToBase64(buffer: ArrayBuffer) {
  const bytes = new Uint8Array(buffer);
  const chars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  let output = "";

  for (let i = 0; i < bytes.length; i += 3) {
    const chunk =
      (bytes[i] << 16) | ((bytes[i + 1] ?? 0) << 8) | (bytes[i + 2] ?? 0);
    output += chars[(chunk >> 18) & 63];
    output += chars[(chunk >> 12) & 63];
    output += i + 1 < bytes.length ? chars[(chunk >> 6) & 63] : "=";
    output += i + 2 < bytes.length ? chars[chunk & 63] : "=";
  }

  return output;
}

export default function DatasetDetailScreen() {
  const palette = useAppTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const {
    address,
    isConnected,
    configError,
    activeMutation,
    transactionError,
    beginMutation,
    completeMutation,
    failMutation,
    openConnectModal,
  } = useWalletStore();
  const { preferredCurrency, rates } = useCurrencyStore();
  const fetchPurchases = useMarketplaceStore((state) => state.fetchPurchases);

  const [dataset, setDataset] = useState<MarketplaceDataItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPurchased, setIsPurchased] = useState(false);
  const [accessLoading, setAccessLoading] = useState(false);
  const [integrity, setIntegrity] = useState<IntegrityStatus>("verifying");
  const [integrityDetail, setIntegrityDetail] = useState<string | undefined>();
  const [downloadStep, setDownloadStep] = useState<DownloadStep>("idle");
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const uuid = useMemo(() => {
    if (!id) return null;
    try {
      return bytes32ToUuid(id);
    } catch {
      return id;
    }
  }, [id]);

  const loadDataset = useCallback(async () => {
    if (!uuid) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const item = await backend.getMarketplaceItem(uuid);
      setDataset(item);

      void verifyDatasetIntegrity({
        datasetUrl: item.dataset_url,
        datasetHash: item.dataset_hash,
        signatureUrl: item.signature_url,
        signatureHash: item.signature_hash,
      }).then((result) => {
        setIntegrity(result.status);
        setIntegrityDetail(result.detail);
      });
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Failed to load dataset.",
      );
    } finally {
      setLoading(false);
    }
  }, [uuid]);

  const checkAccess = useCallback(async () => {
    if (!uuid || !address || !isConnected) {
      setIsPurchased(false);
      return;
    }

    setAccessLoading(true);
    try {
      const response = await backend.checkAccess(uuid, {
        wallet_type: "evm",
        address,
      });
      setIsPurchased(response.has_access);
    } catch {
      setIsPurchased(false);
    } finally {
      setAccessLoading(false);
    }
  }, [address, isConnected, uuid]);

  useEffect(() => {
    void loadDataset();
  }, [loadDataset]);

  useEffect(() => {
    void checkAccess();
  }, [checkAccess]);

  async function handleBuy() {
    if (!dataset) {
      return;
    }

    if (!isConnected) {
      await openConnectModal();
      return;
    }

    if (configError) {
      failMutation(configError);
      return;
    }

    beginMutation("buy");

    try {
      const txHash = await buyItemTx(dataset.id, BigInt(dataset.price));
      completeMutation(txHash);
      await checkAccess();
      if (address) {
        await fetchPurchases(address, true);
      }
      Alert.alert(
        "Purchase confirmed",
        "The transaction mined successfully. You can now release the decryption key.",
      );
    } catch (nextError) {
      failMutation(
        nextError instanceof Error ? nextError.message : "Purchase failed.",
      );
    }
  }

  async function handleDownload() {
    if (!dataset || !address || !uuid) {
      return;
    }

    setDownloadError(null);

    try {
      setDownloadStep("authorizing");
      const keyResp = await backend.requestKeyRelease(uuid, {
        wallet_type: "evm",
        address,
      });

      setDownloadStep("fetching");
      const ciphertextUrl = resolveIpfsUrl(dataset.dataset_url);
      const ciphertextResp = await fetch(ciphertextUrl);
      if (!ciphertextResp.ok) {
        throw new Error(`Failed to fetch dataset (${ciphertextResp.status})`);
      }

      const ciphertext = await ciphertextResp.arrayBuffer();

      setDownloadStep("decrypting");
      const key = decodeBase64(keyResp.key_b64);
      const nonce = decodeBase64(keyResp.nonce_b64);
      const plaintext = await decryptAesGcm({
        ciphertext,
        key,
        nonce,
        aad: utf8Bytes(uuid),
      });

      setDownloadStep("saving");
      const file = new FileSystem.File(
        FileSystem.Paths.document,
        `${uuid}.csv`,
      );
      file.create({ intermediates: true, overwrite: true });
      file.write(arrayBufferToBase64(plaintext), { encoding: "base64" });

      setDownloadStep("idle");

      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(file.uri, {
          mimeType: "text/csv",
          dialogTitle: `Open ${dataset.title}`,
        });
      } else {
        Alert.alert("Downloaded", `Saved to ${file.uri}`);
      }
    } catch (nextError) {
      setDownloadStep("idle");
      setDownloadError(
        nextError instanceof Error ? nextError.message : "Download failed.",
      );
    }
  }

  if (loading) {
    return (
      <SafeAreaView
        edges={["top"]}
        style={[styles.container, { backgroundColor: palette.background }]}
      >
        <Stack.Screen options={{ title: "Dataset" }} />
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={palette.tint} />
        </View>
      </SafeAreaView>
    );
  }

  if (error || !dataset) {
    return (
      <SafeAreaView
        edges={["top"]}
        style={[styles.container, { backgroundColor: palette.background }]}
      >
        <Stack.Screen options={{ title: "Dataset" }} />
        <View style={styles.contentWrap}>
          <ErrorPanel
            message={error ?? "Dataset not found"}
            onRetry={() => void loadDataset()}
          />
        </View>
      </SafeAreaView>
    );
  }

  const ethAmount = Number.parseFloat(weiToEth(dataset.price));
  const convertedAmount = convertEthToCurrency(
    ethAmount,
    preferredCurrency,
    rates,
  );
  const displayPrice =
    convertedAmount !== null
      ? formatCurrencyAmount(convertedAmount, preferredCurrency)
      : `${ethAmount.toLocaleString("en-US", { maximumFractionDigits: 4 })} ETH`;

  const isDownloading = downloadStep !== "idle";
  const buyLoading = activeMutation === "buy";

  return (
    <SafeAreaView
      edges={["top"]}
      style={[styles.container, { backgroundColor: palette.background }]}
    >
      <Stack.Screen
        options={{ title: dataset.title, headerBackTitle: "Home" }}
      />
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.hero}>
          <Text style={[styles.eyebrow, { color: palette.subtleText }]}>
            Dataset detail
          </Text>
          <Text style={[styles.title, { color: palette.text }]}>
            {dataset.title}
          </Text>
          <View style={styles.heroMeta}>
            <StatusPill
              label={
                isPurchased
                  ? "Purchased"
                  : accessLoading
                    ? "Checking access"
                    : "Available"
              }
              tone={isPurchased ? "success" : "info"}
            />
            <Text style={[styles.price, { color: palette.text }]}>
              {displayPrice}
            </Text>
          </View>
        </View>

        <IntegrityBadge status={integrity} detail={integrityDetail} />

        <SurfaceCard style={styles.card}>
          <Text style={[styles.sectionTitle, { color: palette.text }]}>
            Description
          </Text>
          <Text style={[styles.bodyCopy, { color: palette.subtleText }]}>
            {dataset.description}
          </Text>
        </SurfaceCard>

        <SurfaceCard style={styles.card}>
          <Text style={[styles.sectionTitle, { color: palette.text }]}>
            Listing details
          </Text>
          <View style={styles.metaRow}>
            <Text style={[styles.metaLabel, { color: palette.subtleText }]}>
              Seller
            </Text>
            <Text style={[styles.metaValue, { color: palette.text }]}>
              {truncateAddress(dataset.seller)}
            </Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={[styles.metaLabel, { color: palette.subtleText }]}>
              Demand
            </Text>
            <Text style={[styles.metaValue, { color: palette.text }]}>
              {formatPurchaseCount(dataset.purchase_count)}
            </Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={[styles.metaLabel, { color: palette.subtleText }]}>
              Listing ID
            </Text>
            <Text
              style={[styles.metaValue, { color: palette.text }]}
              numberOfLines={1}
            >
              {dataset.id}
            </Text>
          </View>
        </SurfaceCard>

        {transactionError ? <ErrorPanel message={transactionError} /> : null}
        {downloadError ? <ErrorPanel message={downloadError} /> : null}

        <SurfaceCard style={styles.card}>
          <Text style={[styles.sectionTitle, { color: palette.text }]}>
            Actions
          </Text>
          {isPurchased ? (
            <AppButton
              label={
                isDownloading
                  ? `${downloadStep.charAt(0).toUpperCase()}${downloadStep.slice(1)}…`
                  : "Release Key & Download"
              }
              onPress={() => void handleDownload()}
              loading={isDownloading}
            />
          ) : (
            <AppButton
              label={isConnected ? "Buy Dataset" : "Connect Wallet to Buy"}
              onPress={() => void handleBuy()}
              loading={buyLoading}
              disabled={!!configError && isConnected}
            />
          )}
          {configError && isConnected ? (
            <Text style={[styles.bodyCopy, { color: palette.danger }]}>
              {configError}
            </Text>
          ) : null}
          {!isConnected ? (
            <Text style={[styles.bodyCopy, { color: palette.subtleText }]}>
              Wallet connection is required for contract purchase and key
              release.
            </Text>
          ) : null}
        </SurfaceCard>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  contentWrap: {
    padding: AppTheme.spacing.md,
  },
  content: {
    paddingHorizontal: AppTheme.spacing.md,
    paddingVertical: AppTheme.spacing.md,
    paddingBottom: AppTheme.spacing.xxl,
    gap: AppTheme.spacing.md,
  },
  hero: {
    gap: AppTheme.spacing.sm,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  title: {
    fontSize: 30,
    fontWeight: "800",
    lineHeight: 36,
  },
  heroMeta: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: AppTheme.spacing.md,
  },
  price: {
    fontSize: 17,
    fontWeight: "800",
  },
  card: {
    gap: AppTheme.spacing.md,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "800",
  },
  bodyCopy: {
    fontSize: 14,
    lineHeight: 21,
  },
  metaRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: AppTheme.spacing.md,
  },
  metaLabel: {
    fontSize: 13,
    fontWeight: "700",
    minWidth: 82,
  },
  metaValue: {
    fontSize: 13,
    fontWeight: "600",
    flex: 1,
    textAlign: "right",
  },
});

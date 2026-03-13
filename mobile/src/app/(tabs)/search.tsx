import React from "react";
import { FlatList, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";

import DatasetCard from "@/components/dataset-card";
import ErrorPanel from "@/components/error-panel";
import SearchBar from "@/components/search-bar";
import SkeletonCard from "@/components/skeleton-card";
import { SurfaceCard } from "@/components/ui/surface-card";
import { AppTheme } from "@/constants/theme";
import { useAppTheme } from "@/hooks/use-app-theme";
import { useSearchStore } from "@/src/stores/search-store";

export default function SearchScreen() {
  const palette = useAppTheme();
  const {
    query,
    submittedQuery,
    resultCount,
    isSearching,
    error,
    results,
    setQuery,
    submitSearch,
    clearSearch,
  } = useSearchStore();

  return (
    <SafeAreaView
      edges={["top"]}
      style={[styles.container, { backgroundColor: palette.background }]}
    >
      <FlatList
        data={results}
        keyExtractor={(item) => item.item.id}
        renderItem={({ item }) => (
          <DatasetCard
            item={item.item}
            onPress={() => router.push(`/dataset/${item.item.id}`)}
          />
        )}
        contentContainerStyle={styles.content}
        ItemSeparatorComponent={() => (
          <View style={{ height: AppTheme.spacing.md }} />
        )}
        ListHeaderComponent={
          <View style={styles.header}>
            <Text style={[styles.eyebrow, { color: palette.subtleText }]}>
              Semantic search
            </Text>
            <Text style={[styles.title, { color: palette.text }]}>
              Find datasets by intent
            </Text>
            <Text style={[styles.subtitle, { color: palette.subtleText }]}>
              Search by meaning across marketplace listings and bring the
              strongest matches to the top.
            </Text>
            <SearchBar
              value={query}
              onChangeText={setQuery}
              onSubmit={() => void submitSearch()}
              onClear={clearSearch}
            />
            {submittedQuery ? (
              <SurfaceCard muted style={styles.resultBanner}>
                <Text style={[styles.resultCopy, { color: palette.text }]}>
                  {isSearching
                    ? "Searching…"
                    : `${resultCount ?? 0} result${resultCount === 1 ? "" : "s"}`}
                </Text>
                <Text
                  style={[styles.resultHint, { color: palette.subtleText }]}
                >
                  Query: “{submittedQuery}”
                </Text>
              </SurfaceCard>
            ) : (
              <SurfaceCard muted>
                <Text
                  style={[styles.resultHint, { color: palette.subtleText }]}
                >
                  Try “climate risk data”, “financial time series”, or “genomics
                  cohorts”.
                </Text>
              </SurfaceCard>
            )}
            {error ? (
              <ErrorPanel message={error} onRetry={() => void submitSearch()} />
            ) : null}
          </View>
        }
        ListEmptyComponent={
          isSearching ? (
            <View style={styles.skeletonGroup}>
              {Array.from({ length: 3 }).map((_, index) => (
                <SkeletonCard key={`search-loading-${index}`} />
              ))}
            </View>
          ) : (
            <SurfaceCard muted>
              <Text style={[styles.emptyTitle, { color: palette.text }]}>
                {submittedQuery ? "No results yet" : "Ready when you are"}
              </Text>
              <Text style={[styles.resultHint, { color: palette.subtleText }]}>
                {submittedQuery
                  ? "Try broadening the query or describing the dataset by outcome instead of a keyword."
                  : "Search results will appear here after you run a semantic query."}
              </Text>
            </SurfaceCard>
          )
        }
        showsVerticalScrollIndicator={false}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    paddingHorizontal: AppTheme.spacing.md,
    paddingBottom: AppTheme.spacing.xxl,
    gap: AppTheme.spacing.md,
  },
  header: {
    paddingVertical: AppTheme.spacing.md,
    gap: AppTheme.spacing.md,
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
  resultBanner: {
    gap: 6,
  },
  resultCopy: {
    fontSize: 14,
    fontWeight: "700",
  },
  resultHint: {
    fontSize: 14,
    lineHeight: 21,
  },
  skeletonGroup: {
    gap: AppTheme.spacing.md,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: "800",
    marginBottom: AppTheme.spacing.xs,
  },
});

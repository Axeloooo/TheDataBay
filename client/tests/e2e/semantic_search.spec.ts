import {
  test,
  expect,
  type Page,
  type APIRequestContext,
} from "@playwright/test";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ─── Constants ───────────────────────────────────────────────────────────────

const WALLET_STORAGE_KEY = "bridgemart_wallet_v4";
const UPLOAD_STORAGE_KEY = "bridgemart_upload_store_v1";
const BACKEND_URL = "http://localhost:8080";

// Standard Anvil account #0 — deterministic address, no real WalletConnect needed.
const TEST_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266";

// Resolve from this spec file: client/tests/e2e/ → server/tests/integration/services/
const CSV_FIXTURE = path.resolve(
  __dirname,
  "../../../server/tests/integration/services/sample.csv",
);

const SCORE_LABELS_RE = /High match|Moderate match|Low match/;

// Targets a pre-seeded marketplace listing, decoupled from the uploaded file
// (upload flow stops at embedding completion, not on-chain listing creation).
const SEARCH_QUERY = "cardiovascular cohort for binary risk classification";
const SEEDED_TITLE = "Cardio Clinical Cohort";

// ─── Prerequisite check ───────────────────────────────────────────────────────

test.beforeAll(async ({ request }: { request: APIRequestContext }) => {
  const reachable = await request
    .get(`${BACKEND_URL}/api/v1/contract/items/all`, { timeout: 5_000 })
    .then((r) => r.status() < 500)
    .catch(() => false);

  if (!reachable) {
    throw new Error(
      `Backend unreachable at ${BACKEND_URL}. ` +
        "Start it before running e2e tests:\n" +
        "  cd server && uvicorn app.main:app --reload --host 0.0.0.0 --port 8080",
    );
  }
});

// ─── Page Object Model ───────────────────────────────────────────────────────

class SemanticSearchPage {
  constructor(readonly page: Page) {}

  /** Registers an init script that seeds wallet state before the first navigation. */
  async seedLocalStorage(): Promise<void> {
    await this.page.addInitScript(
      ({
        walletKey,
        walletValue,
        uploadKey,
      }: {
        walletKey: string;
        walletValue: string;
        uploadKey: string;
      }) => {
        localStorage.setItem(walletKey, walletValue);
        // Remove any persisted upload session to prevent a resumed-session banner
        // from interfering with the upload flow assertions.
        localStorage.removeItem(uploadKey);
      },
      {
        walletKey: WALLET_STORAGE_KEY,
        // Zustand persist format: { state: <partializedState>, version: N }
        // The wallet store's merge function derives isConnected from address,
        // so seeding a non-null address is sufficient to render the upload form.
        walletValue: JSON.stringify({
          state: { address: TEST_ADDRESS, userDisconnected: false },
          version: 0,
        }),
        uploadKey: UPLOAD_STORAGE_KEY,
      },
    );
  }

  async goHome(): Promise<void> {
    await this.page.goto("/");
  }

  async goUpload(): Promise<void> {
    await this.page.goto("/upload");
  }

  async fillUploadForm(
    title: string,
    description: string,
    price: string,
  ): Promise<void> {
    await this.page.getByLabel("Dataset Title").fill(title);
    await this.page.getByLabel("Description").fill(description);
    await this.page.getByLabel("Price (USDC)").fill(price);
  }

  async uploadCsv(filePath: string): Promise<void> {
    // The file input is hidden; setInputFiles bypasses the click-to-open flow.
    await this.page.locator("#csv-file").setInputFiles(filePath);
  }

  async submitUpload(): Promise<void> {
    await this.page.getByRole("button", { name: "List Dataset" }).click();
  }

  /**
   * Waits up to 90 s for the embedding job to reach "Completed".
   * Fails immediately with a clear message if an "Operation failed" error panel appears.
   */
  async waitForJobCompletion(): Promise<void> {
    const completed = this.page.getByText("Completed", { exact: true });
    const errorHeading = this.page.getByRole("heading", {
      name: "Operation failed",
    });

    await expect(completed.or(errorHeading)).toBeVisible({ timeout: 90_000 });

    if (await errorHeading.isVisible()) {
      const detail = await errorHeading
        .locator("xpath=..")
        .locator("p")
        .first()
        .textContent()
        .catch(() => null);
      throw new Error(
        `Upload job failed: "${detail?.trim() ?? "unknown error"}". ` +
          `Ensure the backend is running at ${BACKEND_URL}.`,
      );
    }
  }

  /** Asserts at least one completed-output label (Listing ID, Dataset URL, or Signature URL) is visible. */
  async assertAtLeastOneCompletedOutput(): Promise<void> {
    const candidates = [
      this.page.getByText("Listing ID", { exact: true }),
      this.page.getByText("Dataset URL", { exact: true }),
      this.page.getByText("Signature URL", { exact: true }),
    ];
    const visibility = await Promise.all(candidates.map((l) => l.isVisible()));
    expect(visibility.some(Boolean)).toBe(true);
  }

  /** Asserts zero score-label badges are present (browse / pre-search mode). */
  async assertNoScoreBadge(): Promise<void> {
    await expect(this.page.getByText(SCORE_LABELS_RE)).toHaveCount(0);
  }

  async runSearch(query: string): Promise<void> {
    const input = this.page.getByPlaceholder(
      "Search datasets by meaning, not keywords",
    );
    await input.fill(query);
    await this.page.getByRole("button", { name: "Search" }).click();
  }

  /** Waits for the navbar result-count addon to show a non-searching count. */
  async waitForSearchResults(): Promise<void> {
    await expect(this.page.getByText(/\d+ results/)).toBeVisible({
      timeout: 30_000,
    });
  }

  async assertResultCardVisible(title: string): Promise<void> {
    await expect(this.page.getByText(title)).toBeVisible({ timeout: 30_000 });
  }

  /** Asserts at least one score badge is visible (search mode). */
  async assertScoreBadgeVisible(): Promise<void> {
    await expect(this.page.getByText(SCORE_LABELS_RE).first()).toBeVisible({
      timeout: 30_000,
    });
  }
}

// ─── Test ────────────────────────────────────────────────────────────────────

/**
 * Live-stack golden path.
 *
 * Prerequisites (external, not started by Playwright):
 *   - Anvil node running with the Marketplace contract deployed
 *   - Seeded marketplace data (make seed-anvil) including "Cardio Clinical Cohort"
 *   - Backend running against that contract (uvicorn app.main:app --reload)
 *   - Embeddings indexed for the seeded listings (Tasks 2–4 applied)
 */
test("semantic search golden path", async ({ page }) => {
  const ssp = new SemanticSearchPage(page);

  // Seed localStorage before any navigation so the wallet store hydrates as connected.
  await ssp.seedLocalStorage();

  // ── Browse mode: no score badges should appear ────────────────────────────
  await ssp.goHome();
  await ssp.assertNoScoreBadge();

  // ── Upload flow ───────────────────────────────────────────────────────────
  await ssp.goUpload();
  await expect(
    page.getByRole("heading", { name: "Sell Your Dataset" }),
  ).toBeVisible();

  await ssp.fillUploadForm(
    "E2E Test Dataset",
    "Automated end-to-end test dataset for semantic search pipeline validation",
    "12.50",
  );
  await ssp.uploadCsv(CSV_FIXTURE);
  await ssp.submitUpload();
  await ssp.waitForJobCompletion();
  await ssp.assertAtLeastOneCompletedOutput();

  // ── Search flow ───────────────────────────────────────────────────────────
  // Navigate back to home; confirm still no score badges before searching.
  await ssp.goHome();
  await ssp.assertNoScoreBadge();

  // Run a semantic query that targets the seeded "Cardio Clinical Cohort" listing.
  await ssp.runSearch(SEARCH_QUERY);
  await ssp.waitForSearchResults();

  // The seeded card must appear and carry a visible score badge.
  await ssp.assertResultCardVisible(SEEDED_TITLE);
  await ssp.assertScoreBadgeVisible();
});

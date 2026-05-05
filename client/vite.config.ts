/// <reference types="vitest" />
import path from "path";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig, loadEnv } from "vite";
import { configDefaults } from "vitest/config";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load all vars (empty prefix) from the monorepo root (..)
  const env = loadEnv(mode, path.resolve(__dirname, ".."), "");

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    define: {
      // Remap canonical env var names → VITE_* so client source is unchanged.
      // Fall back to VITE_* prefixed names so Docker build-arg ENV vars are
      // picked up when there is no root .env file (e.g. production builds).
      "import.meta.env.VITE_API_URL": JSON.stringify(
        env.API_URL || env.VITE_API_URL || "http://localhost:8080"
      ),
      "import.meta.env.VITE_CONTRACT_ADDRESS": JSON.stringify(
        env.CONTRACT_ADDRESS || env.VITE_CONTRACT_ADDRESS || ""
      ),
      "import.meta.env.VITE_USDC_TOKEN_ADDRESS": JSON.stringify(
        env.USDC_TOKEN_ADDRESS || env.VITE_USDC_TOKEN_ADDRESS || ""
      ),
      "import.meta.env.VITE_CADC_TOKEN_ADDRESS": JSON.stringify(
        env.CADC_TOKEN_ADDRESS || env.VITE_CADC_TOKEN_ADDRESS || ""
      ),
      "import.meta.env.VITE_PINATA_GATEWAY_URL": JSON.stringify(
        env.PINATA_GATEWAY_URL ||
          env.VITE_PINATA_GATEWAY_URL ||
          "https://gateway.pinata.cloud"
      ),
      "import.meta.env.VITE_WALLETCONNECT_PROJECT_ID": JSON.stringify(
        env.WALLETCONNECT_PROJECT_ID || env.VITE_WALLETCONNECT_PROJECT_ID || ""
      ),
      "import.meta.env.VITE_CHAIN_ID": JSON.stringify(
        env.CHAIN_ID || env.VITE_CHAIN_ID || "31337"
      ),
      // WalletConnect packages reference Node.js `global`
      global: "globalThis",
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./tests/setup.ts"],
      exclude: [...configDefaults.exclude, "tests/e2e/**"],
    },
  };
});

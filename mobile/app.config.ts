import type { ExpoConfig } from "expo/config";

function readEnv(name: string, fallback = "") {
  const value = process.env[name];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

const config: ExpoConfig = {
  name: "TheDataBay",
  slug: "thedatabay",
  version: "1.0.0",
  orientation: "portrait",
  icon: "./assets/images/icon.png",
  scheme: "thedatabay",
  userInterfaceStyle: "automatic",
  newArchEnabled: true,
  ios: {
    supportsTablet: true,
  },
  android: {
    adaptiveIcon: {
      backgroundColor: "#E6F4FE",
      foregroundImage: "./assets/images/android-icon-foreground.png",
      backgroundImage: "./assets/images/android-icon-background.png",
      monochromeImage: "./assets/images/android-icon-monochrome.png",
    },
    edgeToEdgeEnabled: true,
    predictiveBackGestureEnabled: false,
  },
  web: {
    output: "static",
    favicon: "./assets/images/favicon.png",
  },
  plugins: [
    ["expo-router", { root: "src/app" }],
    [
      "expo-splash-screen",
      {
        image: "./assets/images/splash-icon.png",
        imageWidth: 200,
        resizeMode: "contain",
        backgroundColor: "#ffffff",
        dark: {
          backgroundColor: "#000000",
        },
      },
    ],
    "expo-secure-store",
  ],
  experiments: {
    typedRoutes: true,
    reactCompiler: false,
  },
  extra: {
    apiUrl: readEnv("API_URL", "http://localhost:8080"),
    pinataGatewayUrl: readEnv(
      "PINATA_GATEWAY_URL",
      "https://gateway.pinata.cloud",
    ),
    walletConnectProjectId: readEnv("WALLETCONNECT_PROJECT_ID"),
    contractAddress: readEnv("CONTRACT_ADDRESS"),
    paymentTokenAddress: readEnv("PAYMENT_TOKEN_ADDRESS"),
    cadcTokenAddress: readEnv("CADC_TOKEN_ADDRESS"),
    chainId: readEnv("CHAIN_ID", "31337"),
    rpcUrl: readEnv("RPC_URL", "http://127.0.0.1:8545"),
    explorerUrl: readEnv("EXPLORER_URL"),
  },
};

export default config;

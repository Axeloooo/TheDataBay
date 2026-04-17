import type {
  WalletConnectorType,
  WalletRuntime,
  WalletSessionSnapshot,
} from "./types";

const WC_PROJECT_ID = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID as
  | string
  | undefined;

const VITE_CHAIN_ID = import.meta.env.VITE_CHAIN_ID as string | undefined;

const WC_CONFIG_ERROR =
  !WC_PROJECT_ID || WC_PROJECT_ID.trim() === ""
    ? "WalletConnect project ID is not configured. Set VITE_WALLETCONNECT_PROJECT_ID."
    : null;

const CHAIN_NAMES: Record<number, string> = {
  1: "Ethereum",
  11155111: "Sepolia",
  31337: "Anvil",
};

function resolveChainId(): number {
  if (VITE_CHAIN_ID) {
    const parsed = parseInt(VITE_CHAIN_ID, 10);
    if (!isNaN(parsed) && parsed > 0) return parsed;
  }
  return 1;
}

function chainName(chainId: number): string {
  return CHAIN_NAMES[chainId] ?? `Chain ${chainId}`;
}

type EthereumWindowProvider = {
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
  on?: (event: string, callback: (...args: unknown[]) => void) => void;
  removeListener?: (
    event: string,
    callback: (...args: unknown[]) => void,
  ) => void;
};

function getWindowEthereum(): EthereumWindowProvider | null {
  if (typeof window === "undefined") return null;
  return (window.ethereum as EthereumWindowProvider | undefined) ?? null;
}

function buildEmptySnapshot(): WalletSessionSnapshot {
  return {
    address: null,
    chainId: null,
    chainName: null,
    walletName: null,
    walletIcon: null,
    connectorType: null,
    isConnected: false,
    isConnecting: false,
  };
}

function buildSnapshot(
  address: string | null,
  cid: number | null,
  connector: WalletConnectorType | null,
  walletName: string | null = null,
  walletIcon: string | null = null,
  isConnecting = false,
): WalletSessionSnapshot {
  return {
    address,
    chainId: cid,
    chainName: cid !== null ? chainName(cid) : null,
    walletName,
    walletIcon,
    connectorType: connector,
    isConnected: !!address,
    isConnecting,
  };
}

function normalizeFirstAccount(accounts: unknown): string | null {
  if (!Array.isArray(accounts) || accounts.length === 0) return null;
  const first = accounts[0];
  return typeof first === "string" && first.length > 0 ? first : null;
}

// Structural type covering the EthereumProvider API we actually use.
// Avoids importing the class at the module level (which would pull in
// Node.js-dependent polyfills and crash the app before it renders).
type WcEthereumProvider = {
  accounts: string[];
  chainId: number;
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  on(event: string, listener: (...args: unknown[]) => void): void;
  request(args: { method: string; params?: unknown[] }): Promise<unknown>;
};

class WalletRuntimeImpl implements WalletRuntime {
  private wcProvider: WcEthereumProvider | null = null;
  private activeConnector: WalletConnectorType | null = null;
  private listeners: Set<(snapshot: WalletSessionSnapshot) => void> = new Set();
  private currentSnapshot: WalletSessionSnapshot = buildEmptySnapshot();
  private wcInitPromise: Promise<WcEthereumProvider> | null = null;
  private injectedListenersAttached = false;

  private notify(snapshot: WalletSessionSnapshot): void {
    this.currentSnapshot = snapshot;
    for (const listener of this.listeners) {
      listener(snapshot);
    }
  }

  private async initWcProvider(): Promise<WcEthereumProvider> {
    if (this.wcProvider) return this.wcProvider;
    if (this.wcInitPromise) return this.wcInitPromise;

    this.wcInitPromise = (async () => {
      // Dynamic import keeps WalletConnect out of the initial bundle so that
      // missing Node.js polyfills (Buffer, process, etc.) don't crash the app
      // on startup — the provider is only loaded when the user connects.
      const { EthereumProvider } =
        await import("@walletconnect/ethereum-provider");
      const configuredChain = resolveChainId();
      const provider = await EthereumProvider.init({
        projectId: WC_PROJECT_ID!,
        chains: [configuredChain],
        showQrModal: true,
        metadata: {
          name: "BridgeMart",
          description: "Decentralized dataset marketplace",
          url: "https://bridgemart.app",
          icons: ["https://bridgemart.app/icon.png"],
        },
      });

      provider.on("accountsChanged", (accounts: unknown) => {
        if (this.activeConnector !== "walletconnect") return;
        const address = normalizeFirstAccount(accounts);
        const cid = provider.chainId ?? null;
        this.notify(
          buildSnapshot(address, cid, "walletconnect", "WalletConnect"),
        );
      });

      provider.on("chainChanged", (cid: unknown) => {
        if (this.activeConnector !== "walletconnect") return;
        const numericChainId =
          typeof cid === "number"
            ? cid
            : typeof cid === "string"
              ? parseInt(cid, 16) || parseInt(cid, 10) || null
              : null;
        const address =
          provider.accounts.length > 0 ? provider.accounts[0] : null;
        this.notify(
          buildSnapshot(
            address,
            numericChainId,
            "walletconnect",
            "WalletConnect",
          ),
        );
      });

      provider.on("disconnect", () => {
        if (this.activeConnector !== "walletconnect") return;
        this.activeConnector = null;
        this.notify(buildEmptySnapshot());
      });

      this.wcProvider = provider;
      return provider;
    })();

    return this.wcInitPromise;
  }

  private attachInjectedListeners(): void {
    if (this.injectedListenersAttached) return;
    const ethereum = getWindowEthereum();
    if (!ethereum?.on) return;

    ethereum.on("accountsChanged", (...args: unknown[]) => {
      if (this.activeConnector !== "injected") return;
      const accounts = args[0];
      const address = normalizeFirstAccount(accounts);
      if (!address) {
        this.activeConnector = null;
        this.notify(buildEmptySnapshot());
      } else {
        this.notify(
          buildSnapshot(
            address,
            this.currentSnapshot.chainId,
            "injected",
            "Browser Wallet",
          ),
        );
      }
    });

    ethereum.on("chainChanged", (...args: unknown[]) => {
      if (this.activeConnector !== "injected") return;
      const chainIdHex = args[0];
      const numericChainId =
        typeof chainIdHex === "string"
          ? parseInt(chainIdHex, 16) || null
          : typeof chainIdHex === "number"
            ? chainIdHex
            : null;
      this.notify(
        buildSnapshot(
          this.currentSnapshot.address,
          numericChainId,
          "injected",
          "Browser Wallet",
        ),
      );
    });

    this.injectedListenersAttached = true;
  }

  async connect(input: {
    connector: WalletConnectorType;
    eip6963Provider?: object;
  }): Promise<void> {
    const { connector, eip6963Provider } = input;

    if (connector === "walletconnect") {
      if (WC_CONFIG_ERROR) throw new Error(WC_CONFIG_ERROR);
      this.notify({ ...this.currentSnapshot, isConnecting: true });
      try {
        const wc = await this.initWcProvider();
        await wc.connect();
        const address = wc.accounts.length > 0 ? wc.accounts[0] : null;
        const cid = wc.chainId ?? null;
        this.activeConnector = "walletconnect";
        this.notify(
          buildSnapshot(address, cid, "walletconnect", "WalletConnect"),
        );
      } catch (error) {
        this.notify({ ...this.currentSnapshot, isConnecting: false });
        throw error;
      }
    } else {
      const ethereum = eip6963Provider
        ? (eip6963Provider as EthereumWindowProvider)
        : getWindowEthereum();
      if (!ethereum) throw new Error("No injected wallet found.");
      this.notify({ ...this.currentSnapshot, isConnecting: true });
      try {
        const accounts = await ethereum.request({
          method: "eth_requestAccounts",
        });
        const address = normalizeFirstAccount(accounts);
        const chainIdHex = await ethereum.request({ method: "eth_chainId" });
        const cid =
          typeof chainIdHex === "string"
            ? parseInt(chainIdHex, 16) || null
            : null;
        this.activeConnector = "injected";
        this.attachInjectedListeners();
        this.notify(buildSnapshot(address, cid, "injected", "Browser Wallet"));
      } catch (error) {
        this.notify({ ...this.currentSnapshot, isConnecting: false });
        throw error;
      }
    }
  }

  async disconnect(): Promise<void> {
    if (this.activeConnector === "walletconnect" && this.wcProvider) {
      try {
        await this.wcProvider.disconnect();
      } catch {
        // swallow — session may already be gone
      }
      // Clear cached provider so next connect() creates a fresh instance
      // without any retained session state.
      this.wcProvider = null;
      this.wcInitPromise = null;
    }
    this.activeConnector = null;
    this.notify(buildEmptySnapshot());
  }

  async restoreSession(): Promise<WalletSessionSnapshot | null> {
    // Try WalletConnect first if project ID is configured
    if (!WC_CONFIG_ERROR) {
      try {
        const wc = await this.initWcProvider();
        if (wc.accounts.length > 0) {
          const address = wc.accounts[0];
          const cid = wc.chainId ?? null;
          this.activeConnector = "walletconnect";
          const snap = buildSnapshot(
            address,
            cid,
            "walletconnect",
            "WalletConnect",
          );
          this.notify(snap);
          return snap;
        }
      } catch {
        // WC restore failed; fall through to injected check
      }
    }

    // Try injected (check existing permissions without prompting)
    const ethereum = getWindowEthereum();
    if (ethereum) {
      try {
        const accounts = await ethereum.request({ method: "eth_accounts" });
        const address = normalizeFirstAccount(accounts);
        if (address) {
          const chainIdHex = await ethereum.request({ method: "eth_chainId" });
          const cid =
            typeof chainIdHex === "string"
              ? parseInt(chainIdHex, 16) || null
              : null;
          this.activeConnector = "injected";
          this.attachInjectedListeners();
          const snap = buildSnapshot(
            address,
            cid,
            "injected",
            "Browser Wallet",
          );
          this.notify(snap);
          return snap;
        }
      } catch {
        // no existing injected session
      }
    }

    return null;
  }

  subscribeSession(
    listener: (snapshot: WalletSessionSnapshot) => void,
  ): () => void {
    this.listeners.add(listener);
    // Immediately fire with current state
    listener(this.currentSnapshot);
    return () => {
      this.listeners.delete(listener);
    };
  }

  async getEip1193Provider(): Promise<unknown> {
    if (this.activeConnector === "walletconnect") {
      if (WC_CONFIG_ERROR) throw new Error(WC_CONFIG_ERROR);
      if (!this.wcProvider)
        throw new Error("WalletConnect session is not active.");
      return this.wcProvider;
    }
    if (this.activeConnector === "injected") {
      const ethereum = getWindowEthereum();
      if (!ethereum) throw new Error("No injected wallet found.");
      return ethereum;
    }
    throw new Error("No active wallet session.");
  }

  async switchToConfiguredChain(): Promise<void> {
    if (!VITE_CHAIN_ID) return;
    const targetChainId = resolveChainId();
    const chainIdHex = `0x${targetChainId.toString(16)}`;
    const provider = await this.getEip1193Provider();
    const eip1193 = provider as {
      request: (args: {
        method: string;
        params?: unknown[];
      }) => Promise<unknown>;
    };
    await eip1193.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: chainIdHex }],
    });
  }

  getConnectionMetadata(): {
    configError: string | null;
    availableConnectors: WalletConnectorType[];
  } {
    const availableConnectors: WalletConnectorType[] = ["walletconnect"];
    if (getWindowEthereum()) {
      availableConnectors.push("injected");
    }
    return {
      configError: WC_CONFIG_ERROR,
      availableConnectors,
    };
  }
}

export const walletRuntime: WalletRuntime = new WalletRuntimeImpl();

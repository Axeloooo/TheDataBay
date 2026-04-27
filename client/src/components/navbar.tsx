import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";
import { ModeToggle } from "./mode-toggle";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  Search,
  ArrowLeftRight,
  Wallet,
  Upload,
  X,
  Sparkles,
  CircleHelp,
  Bot,
  ShoppingCart,
} from "lucide-react";

import { Button } from "./ui/button";
import { toast } from "sonner";
import { DisplayCurrencySelector } from "@/components/display-currency-selector";
import { useState } from "react";
import { WalletConnectModal } from "@/components/wallet-connect-modal";
import { useSearchStore } from "@/stores/search-store";
import { useCurrencyStore } from "@/stores/currency-store";
import { useWalletStore } from "@/stores/wallet-store";

function shortAddress(addr: string) {
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}

function Navbar() {
  const [modalOpen, setModalOpen] = useState(false);
  const {
    address,
    isConnected,
    isConnecting,
    disconnect,
    chainName,
    walletName,
  } = useWalletStore();
  const preferredCurrency = useCurrencyStore(
    (state) => state.preferredCurrency,
  );
  const setPreferredCurrency = useCurrencyStore(
    (state) => state.setPreferredCurrency,
  );
  const ratesUnavailable = useCurrencyStore((state) => state.ratesUnavailable);
  const navigate = useNavigate();
  const location = useLocation();
  const query = useSearchStore((state) => state.query);
  const setQuery = useSearchStore((state) => state.setQuery);
  const submitSearch = useSearchStore((state) => state.submitSearch);
  const clearSearch = useSearchStore((state) => state.clearSearch);
  const resultCount = useSearchStore((state) => state.resultCount);
  const isSearching = useSearchStore((state) => state.isSearching);
  const submittedQuery = useSearchStore((state) => state.submittedQuery);

  const executeSearch = () => {
    submitSearch();
    if (location.pathname !== "/") {
      navigate("/");
    }
  };

  const copyAddress = async () => {
    if (!address) return;
    try {
      await navigator.clipboard.writeText(address);
      toast("Address copied to clipboard", {
        description: shortAddress(address),
      });
    } catch (error) {
      console.error("Failed to copy address to clipboard:", error);
      toast("Failed to copy address", {
        description: "Please check your browser permissions and try again.",
      });
    }
  };

  return (
    <div className="w-full px-3 py-3 md:px-4">
      <div className="flex flex-wrap items-center gap-2 md:gap-3">
        <Link
          to="/"
          className="group flex min-w-0 items-center gap-3 rounded-xl border border-border/80 bg-card/65 px-3 py-2 shadow-sm transition hover:border-primary/50 hover:bg-card"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border/70 bg-background/60 text-primary shadow-inner">
            <ArrowLeftRight className="h-4 w-4" />
          </div>
          <div className="min-w-0 leading-tight">
            <div className="font-display truncate text-base font-semibold">
              BridgeMart
            </div>
            <div className="truncate text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
              On-chain dataset exchange
            </div>
          </div>
        </Link>

        <div className="order-3 w-full md:order-2 md:flex-1">
          <InputGroup className="h-11 border-border/80 bg-background/75 shadow-sm backdrop-blur">
            <InputGroupAddon>
              <Search className="h-4 w-4" />
            </InputGroupAddon>
            <InputGroupInput
              placeholder="Search datasets by meaning, not keywords"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  executeSearch();
                }
              }}
              className="text-sm"
            />
            {query && (
              <InputGroupAddon align="inline-end">
                <InputGroupButton
                  aria-label="Clear search"
                  onClick={() => clearSearch()}
                  size="icon-xs"
                >
                  <X className="h-3.5 w-3.5" />
                </InputGroupButton>
              </InputGroupAddon>
            )}
            <InputGroupAddon
              align="inline-end"
              className="hidden text-xs sm:flex"
            >
              {submittedQuery
                ? isSearching
                  ? "Searching"
                  : `${resultCount ?? 0} results`
                : "Marketplace"}
            </InputGroupAddon>
            <InputGroupAddon align="inline-end">
              <InputGroupButton
                onClick={() => executeSearch()}
                className="bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <Sparkles className="h-3.5 w-3.5" />
                Search
              </InputGroupButton>
            </InputGroupAddon>
          </InputGroup>
        </div>

        <div className="order-2 ml-auto flex items-center gap-2 md:order-3">
          <NavLink to="/how-it-works">
            {({ isActive }) => (
              <Button
                variant="ghost"
                className={`h-9 gap-1.5 px-2 text-xs md:px-3 md:text-sm ${
                  isActive ? "bg-accent text-accent-foreground" : ""
                }`}
              >
                <CircleHelp className="h-4 w-4" />
                <span className="hidden md:inline">How it works</span>
              </Button>
            )}
          </NavLink>

          <NavLink to="/agents">
            {({ isActive }) => (
              <Button
                variant="ghost"
                className={`h-9 gap-1.5 px-2 text-xs md:px-3 md:text-sm ${
                  isActive ? "bg-accent text-accent-foreground" : ""
                }`}
              >
                <Bot className="h-4 w-4" />
                <span className="hidden md:inline">Agents</span>
              </Button>
            )}
          </NavLink>

          <DisplayCurrencySelector
            value={preferredCurrency}
            onChange={setPreferredCurrency}
            compact
            title="Quote currency"
            buttonClassName="h-9 px-2 text-xs font-medium md:px-3"
          />

          {isConnected && (
            <Link to="/upload">
              <Button
                variant="secondary"
                className="h-9 gap-1.5 border border-border/80 bg-card/80 px-2 text-xs hover:bg-accent/55 md:px-3 md:text-sm"
              >
                <Upload className="h-4 w-4" />
                <span className="hidden md:inline">Sell Data</span>
              </Button>
            </Link>
          )}

          {isConnected && (
            <NavLink to="/purchase-requests">
              {({ isActive }) => (
                <Button
                  variant="ghost"
                  className={`h-9 gap-1.5 px-2 text-xs md:px-3 md:text-sm ${
                    isActive ? "bg-accent text-accent-foreground" : ""
                  }`}
                >
                  <ShoppingCart className="h-4 w-4" />
                  <span className="hidden md:inline">Requests</span>
                </Button>
              )}
            </NavLink>
          )}

          {!isConnected ? (
            <>
              <Button
                className="h-9 gap-1.5 bg-primary px-2 text-xs text-primary-foreground shadow-sm hover:bg-primary/90 md:px-3 md:text-sm"
                disabled={isConnecting}
                onClick={() => setModalOpen(true)}
              >
                <Wallet className="h-4 w-4" />
                <span className="hidden md:inline">
                  {isConnecting ? "Connecting…" : "Connect Wallet"}
                </span>
              </Button>
              <WalletConnectModal
                open={modalOpen}
                onOpenChange={setModalOpen}
              />
            </>
          ) : (
            <div className="flex items-center gap-1.5 md:gap-2">
              <Button
                variant="outline"
                onClick={() => copyAddress()}
                title={address ?? ""}
                className="h-9 border-border/80 bg-background/80 px-2 font-mono text-[11px] md:text-xs"
              >
                {walletName && (
                  <span className="mr-1 hidden text-muted-foreground md:inline">
                    {walletName}
                  </span>
                )}
                {shortAddress(address!)}
                {chainName && (
                  <span className="ml-1 hidden text-muted-foreground md:inline">
                    · {chainName}
                  </span>
                )}
              </Button>
              <Button
                variant="ghost"
                onClick={() => void disconnect()}
                className="h-9 px-2 text-xs md:px-3 md:text-sm"
              >
                Disconnect
              </Button>
            </div>
          )}

          <ModeToggle />
        </div>
      </div>
      {ratesUnavailable && (
        <p className="mt-2 text-right text-[11px] font-medium text-muted-foreground">
          Live FX feed unavailable; quote conversions may be approximate, but
          settlement is fixed to the listing's token.
        </p>
      )}
    </div>
  );
}

export default Navbar;

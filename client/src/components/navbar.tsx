import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  navigationMenuTriggerStyle,
} from "@/components/ui/navigation-menu";
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
  Hexagon,
  Orbit,
} from "lucide-react";
import { Button } from "./ui/button";
import { useWallet } from "@/providers/wallet-provider";
import { toast } from "sonner";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { useSearch } from "@/context/search-context";
import { useCurrency } from "@/context/currency-context";
import type { DisplayCurrency } from "@/lib/fx";

function shortAddress(addr: string) {
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
}

function Navbar() {
  const { address, isConnected, connect, disconnect } = useWallet();
  const { preferredCurrency, setPreferredCurrency, ratesUnavailable } =
    useCurrency();
  const navigate = useNavigate();
  const location = useLocation();
  const {
    query,
    setQuery,
    submitSearch,
    clearSearch,
    resultCount,
    isSearching,
    submittedQuery,
  } = useSearch();

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
    <header className="w-full border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center gap-4 px-4">
        <Link to="/" className="flex items-center gap-2 min-w-45">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border">
            <ArrowLeftRight className="h-5 w-5" />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold">BridgeMart</div>
            <div className="text-xs text-muted-foreground">
              Cross-chain data marketplace
            </div>
          </div>
        </Link>

        <div className="flex flex-1 justify-center">
          <div className="w-full max-w-xl">
            <InputGroup>
              <InputGroupAddon>
                <Search className="h-4 w-4" />
              </InputGroupAddon>
              <InputGroupInput
                placeholder="Search datasets by meaning..."
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    executeSearch();
                  }
                }}
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
              <InputGroupAddon align="inline-end" className="text-xs">
                {submittedQuery
                  ? isSearching
                    ? "Searching..."
                    : `${resultCount ?? 0} results`
                  : "Browse all"}
              </InputGroupAddon>
              <InputGroupAddon align="inline-end">
                <InputGroupButton onClick={() => executeSearch()}>
                  Search
                </InputGroupButton>
              </InputGroupAddon>
            </InputGroup>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <select
            aria-label="Preferred currency"
            className="h-9 rounded-md border bg-background px-2 text-xs"
            value={preferredCurrency}
            onChange={(event) =>
              setPreferredCurrency(event.target.value as DisplayCurrency)
            }
            title="Display currency (payments remain ETH on-chain)"
          >
            <option value="ETH">ETH</option>
            <option value="CAD">CAD</option>
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
            <option value="USDC">USDC</option>
            <option value="SOL">SOL</option>
          </select>
          {ratesUnavailable && (
            <span className="text-xs text-muted-foreground">
              FX unavailable
            </span>
          )}
          <NavigationMenu>
            <NavigationMenuList className="flex items-center gap-1">
              <NavigationMenuItem>
                <NavLink to="/how-it-works">
                  {({ isActive }) => (
                    <NavigationMenuLink
                      className={`${navigationMenuTriggerStyle()} ${
                        isActive ? "font-semibold" : ""
                      }`}
                    >
                      How it works
                    </NavigationMenuLink>
                  )}
                </NavLink>
              </NavigationMenuItem>
            </NavigationMenuList>
          </NavigationMenu>

          {isConnected && (
            <Link to="/upload">
              <Button
                variant="secondary"
                className="hover:cursor-pointer gap-2"
              >
                <Upload className="h-4 w-4" />
                Sell Data
              </Button>
            </Link>
          )}

          {!isConnected ? (
            <DropdownMenu>
              <DropdownMenuTrigger>
                <Button className="hover:cursor-pointer gap-2">
                  <Wallet className="h-4 w-4" />
                  Connect Wallet
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={connect} className="gap-2">
                  <Hexagon className="h-4 w-4" />
                  Ethereum
                </DropdownMenuItem>
                <DropdownMenuItem disabled className="gap-2">
                  <Orbit className="h-4 w-4" />
                  Solana (Coming soon)
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => copyAddress()}
                title={address ?? ""}
                className="font-mono hover:cursor-pointer"
              >
                {shortAddress(address!)}
              </Button>
              <Button
                variant="ghost"
                onClick={disconnect}
                className="hover:cursor-pointer"
              >
                Disconnect
              </Button>
            </div>
          )}

          <ModeToggle />
        </div>
      </div>
    </header>
  );
}

export default Navbar;

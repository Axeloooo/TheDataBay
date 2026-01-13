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
  InputGroupInput,
} from "@/components/ui/input-group";
import { ModeToggle } from "./mode-toggle";
import { Link, NavLink } from "react-router-dom";
import { Search, ArrowLeftRight, Wallet, Upload } from "lucide-react";
import { Button } from "./ui/button";
import { useWallet } from "@/providers/wallet-provider";
import { toast } from "sonner";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";

function shortAddress(addr: string) {
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
}

function Navbar() {
  const { address, isConnected, connect, disconnect } = useWallet();

  const copyAddress = async () => {
    if (!address) return;
    try {
      await navigator.clipboard.writeText(address);
      toast("Address copied to clipboard", {
        description: shortAddress(address),
      });
    } catch {}
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
              <InputGroupInput placeholder="Search" />
              <InputGroupAddon align="inline-end" className="text-xs">
                0 results
              </InputGroupAddon>
            </InputGroup>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <NavigationMenu>
            <NavigationMenuList className="flex items-center gap-1">
              {/* <NavigationMenuItem>
                <NavLink to="/">
                  {({ isActive }) => (
                    <NavigationMenuLink
                      className={`${navigationMenuTriggerStyle()} ${
                        isActive ? "font-semibold" : ""
                      }`}
                    >
                      Marketplace
                    </NavigationMenuLink>
                  )}
                </NavLink>
              </NavigationMenuItem> */}

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
                <DropdownMenuItem onClick={connect}>EVM</DropdownMenuItem>
                <DropdownMenuItem disabled>Solana</DropdownMenuItem>
                <DropdownMenuItem disabled>Bitcoin</DropdownMenuItem>
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

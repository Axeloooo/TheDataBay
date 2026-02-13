import React from "react";
import Navbar from "@/components/navbar";
import { SearchProvider } from "@/context/search-context";

interface LayoutProps {
  children: React.ReactNode;
}

function Layout({ children }: LayoutProps) {
  const messages = [
    "⚠️ BridgeMart is in beta development — flows and APIs may evolve quickly.",
    "🔐 Dataset files are encrypted; key release is gated by on-chain access.",
    "🧪 Localnet tip: verify MetaMask chain + deployed contract address before signing.",
    "🚧 Solana cross-chain support (CCIP roadmap) is coming soon.",
    "⛽ Current settlement is ETH/wei on EVM; multi-asset UX is display-only for now.",
  ];

  return (
    <SearchProvider>
      <>
        <div className="beta-marquee border-b bg-amber-100 text-amber-950">
          <div className="beta-marquee-track">
            {[...messages, ...messages].map((msg, idx) => (
              <span
                key={`${idx}-${msg}`}
                className="beta-marquee-item"
                aria-hidden={idx >= messages.length}
              >
                {msg}
              </span>
            ))}
          </div>
        </div>
        <header className="sticky top-0 z-50 w-full border-b bg-background">
          <div className="container mx-auto flex h-16 items-center px-4">
            <Navbar></Navbar>
          </div>
        </header>
        <main className="flex-1 w-full">
          <div className="container mx-auto px-4 py-6">{children}</div>
        </main>
      </>
    </SearchProvider>
  );
}

export default Layout;

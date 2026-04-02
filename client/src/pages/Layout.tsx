import React from "react";
import Navbar from "@/components/navbar";

interface LayoutProps {
  children: React.ReactNode;
}

function Layout({ children }: LayoutProps) {
  const messages = [
    "🚀 BridgeMart is in active beta — features and APIs are evolving. Check back often.",
    "🔐 Every dataset is AES-encrypted before it reaches IPFS. The decryption key only releases after on-chain purchase.",
    "🤖 AI agents can discover, recommend, and request purchases of datasets on your behalf.",
    "💵 USDC settlement is live. Solana and additional chains are on the roadmap.",
    "💱 Prices display in your preferred quote currency — settlement remains USDC on-chain.",
    "🔗 Connect any EVM wallet — MetaMask, WalletConnect, and more — to start buying or selling datasets.",
  ];

  return (
    <div className="relative min-h-screen overflow-x-clip">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -left-28 top-10 h-72 w-72 rounded-full bg-primary/20 blur-3xl" />
        <div className="absolute right-0 top-64 h-64 w-64 rounded-full bg-chart-4/25 blur-3xl" />
        <div className="absolute bottom-8 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-chart-2/12 blur-3xl" />
      </div>

      <div className="beta-marquee border-y border-border/70 bg-card/55 py-2 text-foreground/90 backdrop-blur">
        <div className="beta-marquee-track px-4">
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

      <div className="sticky top-2 z-50 px-2 md:px-4">
        <div className="mx-auto w-full max-w-7xl rounded-2xl border border-border/80 bg-background/80 shadow-[0_18px_50px_-26px_rgba(15,24,47,0.45)] backdrop-blur-lg">
          <Navbar />
        </div>
      </div>

      <main className="w-full pb-12">
        <div className="mx-auto w-full max-w-7xl px-4 pt-6 md:px-6">{children}</div>
      </main>
    </div>
  );
}

export default Layout;

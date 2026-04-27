import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ArrowLeftRight,
  Shield,
  Coins,
  Download,
  Search,
  Upload,
  Sparkles,
  Lock,
  Database,
  Network,
} from "lucide-react";

function HowItWorks() {
  const steps = [
    {
      icon: Search,
      title: "Search by Meaning",
      description:
        "Describe what your model needs in plain language. BridgeMart ranks datasets by semantic similarity — so the right asset surfaces even when the listing uses different words.",
    },
    {
      icon: Shield,
      title: "Verify Before You Spend",
      description:
        "Every listing exposes SHA-256 integrity proofs and structured metadata. Read everything — commit nothing — until you're sure.",
    },
    {
      icon: Coins,
      title: "Settle On-Chain, Get Provable Access",
      description:
        "A smart contract records your purchase on-chain using the listing's settlement token. No approval queues, no invoices — your access rights are on-chain and verifiable by anyone, anytime.",
    },
    {
      icon: Download,
      title: "Your Key, Your Data",
      description:
        "Once the contract confirms ownership, the decryption key is released. Download from IPFS and verify the payload against the listed hash before using it.",
    },
    {
      icon: Upload,
      title: "Publish Once, Earn Every Time",
      description:
        "Upload your dataset, set a price in the listing's token, and let the contract handle the rest. Every purchase settles automatically — no billing cycles, no chargebacks.",
    },
    {
      icon: ArrowLeftRight,
      title: "Built for What's Next",
      description:
        "Settlement runs on EVM today, supporting USDC and CADC. Multi-chain support for Solana and additional EVM networks is actively in development, while quote currencies remain local-only.",
    },
  ];

  return (
    <div className="space-y-6 pb-6">
      <section className="relative overflow-hidden rounded-3xl border border-border/75 bg-card/75 p-7 shadow-[0_24px_60px_-40px_rgba(15,24,47,0.8)] md:p-9">
        <div className="pointer-events-none absolute -right-12 top-0 h-44 w-44 rounded-full bg-primary/22 blur-3xl" />

        <p className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-background/65 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.11em] text-muted-foreground">
          <Sparkles className="h-3.5 w-3.5" />
          How it works
        </p>
        <h1 className="mt-4 text-balance text-3xl font-semibold leading-tight md:text-4xl">
          From encrypted listing to verified download, with on-chain token
          settlement and quote-only pricing.
        </h1>
        <p className="mt-3 max-w-3xl text-sm text-muted-foreground md:text-base">
          Find the right dataset, confirm its integrity, settle on-chain, and
          download — the entire flow runs without custodians or trust
          assumptions.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {steps.map((step, index) => {
          const Icon = step.icon;
          return (
            <Card
              key={index}
              className="group border-border/75 bg-card/65 transition hover:-translate-y-1 hover:border-primary/45"
            >
              <CardHeader>
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-border/80 bg-background/75 text-primary">
                    <Icon className="h-5 w-5" />
                  </div>
                  <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                    Step {index + 1}
                  </span>
                </div>
                <CardTitle className="text-xl">{step.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-sm leading-relaxed">
                  {step.description}
                </CardDescription>
              </CardContent>
            </Card>
          );
        })}
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <Card className="border-border/75 bg-card/65">
          <CardHeader>
            <CardTitle className="inline-flex items-center gap-2">
              <Lock className="h-5 w-5 text-primary" />
              Trust by Design
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Every dataset is AES-encrypted before it reaches IPFS. The
              decryption key is only released when on-chain ownership is
              confirmed — the contract is the gatekeeper, not a person.
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/75 bg-card/65">
          <CardHeader>
            <CardTitle className="inline-flex items-center gap-2">
              <Database className="h-5 w-5 text-primary" />
              AI-Ready Assets
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Every listing ships with embeddings and structured metadata. Drop
              datasets directly into RAG pipelines, fine-tuning jobs, or
              retrieval benchmarks — no reformatting required.
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/75 bg-card/65">
          <CardHeader>
            <CardTitle className="inline-flex items-center gap-2">
              <Network className="h-5 w-5 text-primary" />
              Interoperable Roadmap
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              EVM settlement (USDC, CADC) is live today. Solana and additional
              EVM chains are on the roadmap — so the datasets you list now will
              reach a broader buyer pool as the network grows.
            </p>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

export default HowItWorks;

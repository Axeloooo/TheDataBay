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
      title: "Discover by Semantics",
      description:
        "Search by intent and meaning to surface datasets that match model tasks, not just keyword tags.",
    },
    {
      icon: Shield,
      title: "Verify Before Purchase",
      description:
        "Inspect SHA-256 integrity proofs, metadata, and signatures before spending any funds.",
    },
    {
      icon: Coins,
      title: "Settle On-Chain",
      description:
        "Pay with ETH and receive deterministic access permissions via smart contracts.",
    },
    {
      icon: Download,
      title: "Decrypt and Download",
      description:
        "Authorized buyers unlock encrypted payloads and download from IPFS with verification details.",
    },
    {
      icon: Upload,
      title: "List and Monetize",
      description:
        "Sellers publish encrypted datasets, define price, and earn from every on-chain purchase.",
    },
    {
      icon: ArrowLeftRight,
      title: "Expand Cross-Chain",
      description:
        "BridgeMart is being prepared for broader interoperability with EVM and Solana ecosystems.",
    },
  ];

  return (
    <div className="space-y-6 pb-6">
      <section className="relative overflow-hidden rounded-3xl border border-border/75 bg-card/75 p-7 shadow-[0_24px_60px_-40px_rgba(15,24,47,0.8)] md:p-9">
        <div className="pointer-events-none absolute -right-12 top-0 h-44 w-44 rounded-full bg-primary/22 blur-3xl" />

        <p className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-background/65 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.11em] text-muted-foreground">
          <Sparkles className="h-3.5 w-3.5" />
          Process walkthrough
        </p>
        <h1 className="mt-4 text-balance text-3xl font-semibold leading-tight md:text-4xl">
          How BridgeMart moves data from listing to authorized access.
        </h1>
        <p className="mt-3 max-w-3xl text-sm text-muted-foreground md:text-base">
          The platform joins semantic discovery, cryptographic verification,
          and on-chain settlement into one buyer flow for AI-ready datasets.
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
              Dataset files are encrypted before listing. Keys are only released
              after contract-level access checks succeed.
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
              Listings include dataset metadata and embeddings that support RAG,
              semantic retrieval, and model training workflows.
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
              Current execution settles on EVM with ETH. Multi-chain and
              cross-ecosystem settlement paths are actively planned.
            </p>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

export default HowItWorks;

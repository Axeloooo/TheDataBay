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
} from "lucide-react";

function HowItWorks() {
  const steps = [
    {
      icon: Search,
      title: "Browse Datasets",
      description:
        "Explore our marketplace of high-quality datasets with embeddings. Filter by domain, size, and vector specifications.",
    },
    {
      icon: Shield,
      title: "Verify Integrity",
      description:
        "Check SHA-256 hashes and vector specifications. All datasets are cryptographically verifiable before purchase.",
    },
    {
      icon: Coins,
      title: "Purchase with Crypto",
      description:
        "Pay securely with ETH on multiple chains. Smart contracts ensure trustless transactions between buyers and sellers.",
    },
    {
      icon: Download,
      title: "Download & Use",
      description:
        "Access your purchased datasets via IPFS. Download CSV data, vector embeddings, and metadata instantly.",
    },
    {
      icon: Upload,
      title: "Sell Your Data",
      description:
        "List your own datasets with embeddings. Set your price, upload to IPFS, and earn ETH from sales.",
    },
    {
      icon: ArrowLeftRight,
      title: "Cross-Chain Compatible",
      description:
        "Future support for multiple blockchains including Solana and EVM networks for broader accessibility.",
    },
  ];

  return (
    <div className="min-h-screen">
      <div className="mx-auto w-full max-w-6xl px-4 py-12">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">How It Works</h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            BridgeMart is a decentralized marketplace for AI-ready datasets with
            vector embeddings. Buy and sell data securely across multiple
            blockchains.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 mb-12">
          {steps.map((step, index) => {
            const Icon = step.icon;
            return (
              <Card key={index}>
                <CardHeader>
                  <div className="flex items-center gap-3 mb-2">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg border bg-primary/10">
                      <Icon className="h-5 w-5 text-primary" />
                    </div>
                    <span className="text-sm font-semibold text-muted-foreground">
                      Step {index + 1}
                    </span>
                  </div>
                  <CardTitle>{step.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription>{step.description}</CardDescription>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <Card className="bg-muted/50">
          <CardHeader>
            <CardTitle>Why Use BridgeMart?</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h3 className="font-semibold mb-2">
                🔒 Decentralized & Trustless
              </h3>
              <p className="text-sm text-muted-foreground">
                No intermediaries. Smart contracts handle all transactions
                securely without requiring trust in a central authority.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-2">🎯 AI-Ready Data</h3>
              <p className="text-sm text-muted-foreground">
                All datasets include vector embeddings for semantic search, RAG,
                and ML applications. Ready to use with your AI pipelines.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-2">🌐 IPFS Storage</h3>
              <p className="text-sm text-muted-foreground">
                Permanent, distributed storage ensures your data is always
                accessible and censorship-resistant.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-2">✅ Verified Quality</h3>
              <p className="text-sm text-muted-foreground">
                Cryptographic hashes guarantee data integrity. Verified sellers
                maintain quality standards.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default HowItWorks;

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Coins, Users, ArrowUpRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useCurrency } from "@/context/currency-context";
import { convertEthToCurrency, formatCurrencyAmount } from "@/lib/fx";

interface RecordCardProps {
  id: string;
  title: string;
  description: string;
  priceEth: string;
  purchaseCount: number;
}

function RecordCard({
  id,
  title,
  description,
  priceEth,
  purchaseCount,
}: RecordCardProps) {
  const navigate = useNavigate();
  const { preferredCurrency, rates } = useCurrency();
  const equivalent =
    preferredCurrency !== "ETH"
      ? convertEthToCurrency(Number(priceEth), preferredCurrency, rates)
      : null;

  return (
    <Card
      className="group relative overflow-hidden border-border/80 bg-card/70 shadow-[0_20px_45px_-36px_rgba(21,32,66,0.95)] transition duration-300 hover:-translate-y-1 hover:border-primary/45 hover:shadow-[0_32px_70px_-40px_rgba(24,38,77,0.95)]"
      onClick={() => navigate(`/dataset/${id}`)}
    >
      <div className="pointer-events-none absolute -right-16 -top-16 h-32 w-32 rounded-full bg-primary/15 blur-2xl transition group-hover:bg-primary/25" />

      <CardHeader className="relative">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="line-clamp-2 text-lg font-semibold leading-snug">
            {title}
          </CardTitle>
          <ArrowUpRight className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-primary" />
        </div>
        <CardDescription className="line-clamp-3 text-sm leading-relaxed">
          {description}
        </CardDescription>
      </CardHeader>

      <CardContent className="relative space-y-4">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Users className="h-3.5 w-3.5" />
          <span>{purchaseCount.toLocaleString()} purchases</span>
        </div>

        <div className="flex items-end justify-between gap-2">
          <Badge variant="secondary" className="rounded-full px-2.5 py-1 font-mono text-xs">
            <span className="inline-flex items-center gap-1">
              <Coins className="h-3 w-3" />
              {priceEth} ETH
            </span>
          </Badge>
          {equivalent !== null && (
            <span className="text-xs text-muted-foreground">
              ~ {formatCurrencyAmount(equivalent, preferredCurrency)}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default RecordCard;

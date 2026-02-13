import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Coins, Users } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useCurrency } from "@/context/currency-context";
import {
  convertEthToCurrency,
  formatCurrencyAmount,
} from "@/lib/fx";

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
      className="hover:shadow-lg transition-shadow cursor-pointer"
      onClick={() => navigate(`/dataset/${id}`)}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <CardTitle className="text-base line-clamp-2">{title}</CardTitle>
        </div>
        <CardDescription className="line-clamp-2">
          {description}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <Users className="h-4 w-4" />
            <span>{purchaseCount.toLocaleString()} purchases</span>
          </div>
        </div>
        <div className="flex items-center justify-between">
          <Badge variant="secondary" className="text-xs font-mono">
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

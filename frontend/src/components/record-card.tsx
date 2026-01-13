import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Database, Table2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface RecordCardProps {
  id: string;
  title: string;
  description: string;
  priceEth: number;
  rows: number;
  columns: number;
  dimension: number;
  verified: boolean;
}

function RecordCard({
  id,
  title,
  description,
  priceEth,
  rows,
  columns,
  dimension,
  verified,
}: RecordCardProps) {
  const navigate = useNavigate();

  return (
    <Card
      className="hover:shadow-lg transition-shadow cursor-pointer"
      onClick={() => navigate(`/dataset/${id}`)}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <CardTitle className="text-base line-clamp-2">{title}</CardTitle>
          {verified && (
            <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0 ml-2" />
          )}
        </div>
        <CardDescription className="line-clamp-2">
          {description}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <Table2 className="h-4 w-4" />
            <span>
              {rows.toLocaleString()} × {columns}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <Database className="h-4 w-4" />
            <span>{dimension}d</span>
          </div>
        </div>
        <div className="flex items-center justify-between">
          <Badge variant="secondary" className="text-xs font-mono">
            {priceEth} ETH
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}

export default RecordCard;

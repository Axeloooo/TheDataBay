import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import type { SettlementCurrency } from "@/types/contract";

const SETTLEMENT_OPTIONS: { currency: SettlementCurrency; icon: string }[] = [
  { currency: "USDC", icon: "/usdc-logo.svg" },
  { currency: "CADC", icon: "/cadc-logo.svg" },
];

interface SettlementCurrencySelectorProps {
  value: SettlementCurrency;
  onChange: (currency: SettlementCurrency) => void;
  className?: string;
  buttonClassName?: string;
  menuClassName?: string;
  compact?: boolean;
}

export function SettlementCurrencySelector({
  value,
  onChange,
  className,
  buttonClassName,
  menuClassName,
  compact = false,
}: SettlementCurrencySelectorProps) {
  const selected =
    SETTLEMENT_OPTIONS.find((option) => option.currency === value) ??
    SETTLEMENT_OPTIONS[0];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            "h-9 gap-2 border-border/80 bg-background/75 font-medium",
            compact ? "px-2 text-xs" : "px-3 text-sm",
            buttonClassName,
            className,
          )}
          title="Settlement token — the on-chain currency buyers will pay in"
        >
          <img
            src={selected.icon}
            alt=""
            aria-hidden="true"
            className="h-4 w-4 shrink-0 rounded-sm object-contain"
          />
          <span>{selected.currency}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className={cn("min-w-[140px]", menuClassName)}
      >
        {SETTLEMENT_OPTIONS.map((option) => (
          <DropdownMenuItem
            key={option.currency}
            onClick={() => onChange(option.currency)}
            className={cn(
              "gap-2 text-xs",
              value === option.currency ? "bg-accent" : "",
            )}
          >
            <img
              src={option.icon}
              alt=""
              aria-hidden="true"
              className="h-4 w-4 shrink-0 rounded-sm object-contain"
            />
            <span>{option.currency}</span>
            {value === option.currency && (
              <span className="ml-auto text-xs">✓</span>
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import {
  DISPLAY_CURRENCY_OPTIONS,
  type DisplayCurrency,
} from "@/lib/fx";

interface DisplayCurrencySelectorProps {
  value: DisplayCurrency;
  onChange: (currency: DisplayCurrency) => void;
  className?: string;
  buttonClassName?: string;
  menuClassName?: string;
  compact?: boolean;
  title?: string;
}

export function DisplayCurrencySelector({
  value,
  onChange,
  className,
  buttonClassName,
  menuClassName,
  compact = false,
  title = "Display currency",
}: DisplayCurrencySelectorProps) {
  const selected =
    DISPLAY_CURRENCY_OPTIONS.find((option) => option.code === value) ??
    DISPLAY_CURRENCY_OPTIONS[0];

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
          title={`${title} - quotes only, settlement stays USDC`}
        >
          <img
            src={selected.icon}
            alt=""
            aria-hidden="true"
            className="h-4 w-4 shrink-0 rounded-sm object-contain"
          />
          <span>{selected.code}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className={cn("min-w-[140px]", menuClassName)}>
        {DISPLAY_CURRENCY_OPTIONS.map((option) => (
          <DropdownMenuItem
            key={option.code}
            onClick={() => onChange(option.code)}
            className={cn(
              "gap-2 text-xs",
              value === option.code ? "bg-accent" : "",
            )}
          >
            <img
              src={option.icon}
              alt=""
              aria-hidden="true"
              className="h-4 w-4 shrink-0 rounded-sm object-contain"
            />
            <span>{option.code}</span>
            {value === option.code && <span className="ml-auto text-xs">✓</span>}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

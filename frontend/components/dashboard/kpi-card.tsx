import type { LucideIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export type KpiCardProps = {
  title: string;
  value: string;
  hint?: string;
  icon?: LucideIcon;
  tone?: "neutral" | "positive" | "negative";
};

export function KpiCard({
  title,
  value,
  hint,
  icon: Icon,
  tone = "neutral",
}: KpiCardProps) {
  return (
    <Card className="border-border/70 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {title}
        </CardTitle>
        {Icon && <Icon className="size-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        <div
          className={cn(
            "text-2xl font-semibold tabular-nums tracking-tight",
            tone === "positive" && "text-emerald-600",
            tone === "negative" && "text-rose-600",
          )}
        >
          {value}
        </div>
        {hint && (
          <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
        )}
      </CardContent>
    </Card>
  );
}

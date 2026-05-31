import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn, formatINR, formatNumber } from "@/lib/utils";

export function MetricCard({
  label,
  value,
  kind = "money",
  note,
  tone = "neutral",
  trend
}: {
  label: string;
  value: number;
  kind?: "money" | "months" | "score";
  note?: string;
  tone?: "neutral" | "good" | "warn" | "bad";
  trend?: "up" | "down" | "flat";
}) {
  const TrendIcon = trend === "up" ? ArrowUpRight : trend === "down" ? ArrowDownRight : Minus;
  return (
    <Card className={cn("overflow-hidden", tone === "bad" && "border-red-200", tone === "warn" && "border-amber-200")}>
      <CardHeader className="flex-row items-start justify-between space-y-0 pb-2">
        <CardTitle className="text-xs uppercase tracking-[0.16em] text-muted-foreground">{label}</CardTitle>
        {trend && <TrendIcon className="size-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold tracking-tight">
          {kind === "money" ? formatINR(value) : kind === "months" ? `${formatNumber(value, 1)} mo` : Math.round(value)}
        </div>
        {note && <p className="mt-2 text-sm text-muted-foreground">{note}</p>}
      </CardContent>
    </Card>
  );
}

"use client";

import Link from "next/link";
import { ArrowRight, RefreshCw, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/hooks/use-api";
import { formatINR, formatNumber } from "@/lib/utils";
import { api } from "@/services/api";
import { PageHeader } from "@/features/shell/page-header";
import { MetricCard } from "./metric-card";

export function DashboardView() {
  const { data, loading, error } = useResource(api.dashboard, []);

  if (loading) return <DashboardSkeleton />;
  if (error) return <div className="rounded-lg border bg-card p-6 text-sm text-red-700">{error}</div>;
  if (!data) return null;

  const metrics = data.metrics;
  return (
    <>
      <PageHeader eyebrow={data.organization.user_type === "startup" ? "Startup founder" : "Freelancer / agency"} title="Cash command center">
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href="/login">Switch demo</Link>
          </Button>
          <Button onClick={() => api.runFinancialAnalysis().then(() => window.location.reload())}>
            <RefreshCw className="size-4" />
            Run analysis
          </Button>
        </div>
      </PageHeader>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Current cash" value={metrics.current_cash} note="Verified from bank/account records" />
        <MetricCard label="Monthly burn" value={metrics.monthly_burn} note="Expenses + active payroll" trend="up" tone={metrics.monthly_burn > 250000 ? "warn" : "neutral"} />
        <MetricCard label="Runway" value={metrics.runway_months} kind="months" note="Cash divided by net burn" tone={metrics.runway_months < 9 ? "bad" : "warn"} />
        <MetricCard label="Risk score" value={metrics.risk_score} kind="score" note="Runway + receivables pressure" tone={metrics.risk_score > 60 ? "bad" : "warn"} />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader className="border-b">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Operational risks</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">Proactive findings generated from verified facts.</p>
              </div>
              <Badge variant="outline">
                <ShieldCheck className="mr-1 size-3" />
                Audited
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 pt-5">
            {data.top_risks.map((risk) => (
              <div key={risk.title} className="rounded-lg border bg-background p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="text-sm font-semibold">{risk.title}</div>
                    <p className="mt-1 text-sm text-muted-foreground">{risk.message}</p>
                  </div>
                  <Badge variant={risk.severity === "high" ? "danger" : "warning"}>{risk.severity}</Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b">
            <CardTitle>Verified finance position</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-5">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-md border bg-background p-3">
                <div className="text-xs text-muted-foreground">Receivables</div>
                <div className="mt-1 text-lg font-semibold">{formatINR(metrics.receivables)}</div>
              </div>
              <div className="rounded-md border bg-background p-3">
                <div className="text-xs text-muted-foreground">Payables 30d</div>
                <div className="mt-1 text-lg font-semibold">{formatINR(metrics.payables_30d)}</div>
              </div>
            </div>
            <div className="rounded-lg bg-primary p-4 text-primary-foreground">
              <div className="text-sm font-semibold">Decision posture</div>
              <p className="mt-2 text-sm leading-6 text-primary-foreground/82">
                With {formatNumber(metrics.runway_months, 1)} months of runway and {formatINR(metrics.overdue_receivables)} overdue, clariFi recommends reviewing cash-positive actions before increasing fixed burn.
              </p>
            </div>
            <Button variant="outline" className="w-full" asChild>
              <Link href="/feed">
                Open CFO feed
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-5">
      <Skeleton className="h-20 w-full" />
      <div className="grid gap-4 md:grid-cols-4">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
      <Skeleton className="h-96" />
    </div>
  );
}

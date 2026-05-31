"use client";

import { TrendingUp } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/hooks/use-api";
import { formatINR, formatNumber } from "@/lib/utils";
import { api } from "@/services/api";
import { PageHeader } from "@/features/shell/page-header";

export function FundraisingView() {
  const [notice, setNotice] = useState<string | null>(null);
  const { data, loading, error } = useResource(api.dashboard, []);

  async function run() {
    await api.runFundraising();
    setNotice("Fundraising timing workflow ran and wrote an auditable recommendation if the threshold was crossed.");
  }

  if (loading) return <Skeleton className="h-96" />;
  if (error) return <div className="rounded-lg border bg-card p-6 text-sm text-red-700">{error}</div>;
  if (!data) return null;

  const runway = data.metrics.runway_months;
  const threshold = 7;
  const status = runway <= threshold ? "Start fundraising now" : "Prepare, but not urgent this week";

  return (
    <>
      <PageHeader eyebrow="Fundraising timing" title="Runway versus raise timeline">
        <Button onClick={run}>
          <TrendingUp className="size-4" />
          Run workflow
        </Button>
      </PageHeader>
      {notice ? <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div> : null}
      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader className="border-b">
            <div className="flex items-center justify-between">
              <CardTitle>Decision</CardTitle>
              <Badge variant={runway <= threshold ? "danger" : "default"}>{status}</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-5">
            <div className="grid gap-3 md:grid-cols-3">
              <Fact label="Current runway" value={`${formatNumber(runway, 1)} mo`} />
              <Fact label="Raise duration" value="5 mo" />
              <Fact label="Buffer" value="2 mo" />
            </div>
            <div className="rounded-lg border bg-background p-4 text-sm leading-6 text-muted-foreground">
              Rule: if runway is less than or equal to fundraising duration plus buffer, clariFi recommends starting now. Current cash is {formatINR(data.metrics.current_cash)} and monthly burn is {formatINR(data.metrics.monthly_burn)}.
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Evidence</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-5">
            {data.facts.filter((fact) => ["runway_months", "current_cash", "monthly_burn"].includes(fact.fact_type)).map((fact) => (
              <div key={fact.id} className="rounded-md border bg-background p-3">
                <div className="text-sm font-semibold">{fact.fact_type}</div>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">{fact.formula}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-background p-4">
      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{label}</div>
      <div className="mt-2 text-xl font-semibold">{value}</div>
    </div>
  );
}

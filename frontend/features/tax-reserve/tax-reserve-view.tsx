"use client";

import { ReceiptText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/hooks/use-api";
import { formatINR } from "@/lib/utils";
import { api } from "@/services/api";
import { PageHeader } from "@/features/shell/page-header";

export function TaxReserveView() {
  const { data, loading, error } = useResource(api.facts, []);

  if (loading) return <Skeleton className="h-96" />;
  if (error) return <div className="rounded-lg border bg-card p-6 text-sm text-red-700">{error}</div>;
  if (!data) return null;

  const income = data.find((fact) => fact.fact_type === "income_received_90d");
  const reserve = data.find((fact) => fact.fact_type === "suggested_tax_reserve");

  return (
    <>
      <PageHeader eyebrow="Tax reserve agent" title="Estimated reserve from received income" />
      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader className="border-b">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <ReceiptText className="size-4" />
                Reserve estimate
              </CardTitle>
              <Badge variant="warning">Estimate only</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-5">
            <div className="grid gap-3 md:grid-cols-2">
              <Fact label="Income received" value={formatINR(income?.value ?? 0)} />
              <Fact label="Suggested reserve" value={formatINR(reserve?.value ?? 0)} />
            </div>
            <div className="rounded-lg border bg-background p-4 text-sm leading-6 text-muted-foreground">
              This uses configurable reserve rules from deterministic engines. It is not tax or legal advice; confirm with a qualified professional before filing or moving funds.
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Audit evidence</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-5">
            {[income, reserve].filter(Boolean).map((fact) => (
              <div key={fact!.id} className="rounded-md border bg-background p-3">
                <div className="text-sm font-semibold">{fact!.fact_type}</div>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">{fact!.formula}</p>
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

"use client";

import { useState } from "react";
import { BriefcaseBusiness } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/hooks/use-api";
import { formatINR, formatNumber } from "@/lib/utils";
import { api } from "@/services/api";
import { PageHeader } from "@/features/shell/page-header";

export function ClientProfitabilityView() {
  const { data, loading, error } = useResource(api.receivables, []);
  const [deliveryCost, setDeliveryCost] = useState(38000);
  const [hours, setHours] = useState(40);

  if (loading) return <Skeleton className="h-96" />;
  if (error) return <div className="rounded-lg border bg-card p-6 text-sm text-red-700">{error}</div>;
  if (!data) return null;

  const invoice = data[0];
  const revenue = invoice ? invoice.amount - invoice.paid_amount : 0;
  const margin = revenue > 0 ? ((revenue - deliveryCost) / revenue) * 100 : 0;
  const hourly = hours > 0 ? (revenue - deliveryCost) / hours : 0;

  return (
    <>
      <PageHeader eyebrow="Client profitability" title="Client margin from invoice-backed revenue" />
      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader className="border-b">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <BriefcaseBusiness className="size-4" />
                {invoice?.customer_name ?? "No client selected"}
              </CardTitle>
              <Badge variant="outline">Needs time/cost input</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-5">
            {!invoice ? (
              <div className="rounded-lg border bg-background p-6 text-sm text-muted-foreground">No receivable invoice found for profitability analysis.</div>
            ) : (
              <>
                <div className="grid gap-3 md:grid-cols-3">
                  <Fact label="Invoice revenue" value={formatINR(revenue)} />
                  <Fact label="Estimated margin" value={`${formatNumber(margin, 1)}%`} />
                  <Fact label="Profit / hour" value={formatINR(hourly)} />
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <label className="text-sm font-medium">Estimated delivery cost</label>
                    <Input type="number" value={deliveryCost} onChange={(event) => setDeliveryCost(Number(event.target.value))} />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Estimated hours</label>
                    <Input type="number" value={hours} onChange={(event) => setHours(Number(event.target.value))} />
                  </div>
                </div>
                <div className="rounded-lg border bg-background p-4 text-sm leading-6 text-muted-foreground">
                  Revenue comes from backend invoices. Time tracking is not integrated yet, so clariFi asks for a project cost/time estimate instead of inventing profitability.
                </div>
              </>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Evidence</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-5">
            {invoice ? (
              <div className="rounded-md border bg-background p-3">
                <div className="text-sm font-semibold">{invoice.invoice_number}</div>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  {formatINR(revenue)} owed by {invoice.customer_name}, due {invoice.due_on}.
                </p>
              </div>
            ) : <p className="text-sm text-muted-foreground">No invoice evidence available.</p>}
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

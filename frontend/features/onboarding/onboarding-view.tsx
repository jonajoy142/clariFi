"use client";

import { useRouter } from "next/navigation";
import { Building2, CheckCircle2, DatabaseZap, PlugZap, UserRoundCog } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SegmentedControl } from "@/components/ui/tabs";
import { PageHeader } from "@/features/shell/page-header";
import { api, ensureSession } from "@/services/api";
import { formatINR, formatNumber } from "@/lib/utils";
import type { DashboardSummary, UserType } from "@/types/api";

const connectorOptions = {
  startup: [
    { type: "zoho_books", label: "Zoho Books", note: "Invoices, bills, payables" },
    { type: "stripe", label: "Stripe", note: "Revenue and processing fees" },
    { type: "razorpay", label: "Razorpay", note: "India payment collections" },
    { type: "gmail", label: "Gmail", note: "Invoice and vendor context" },
    { type: "google_drive", label: "Google Drive", note: "Contracts and policy docs" },
    { type: "manual_csv", label: "Manual CSV", note: "Fallback financial truth source" }
  ],
  freelancer: [
    { type: "stripe", label: "Stripe", note: "Client payments" },
    { type: "razorpay", label: "Razorpay", note: "Payment collections" },
    { type: "gmail", label: "Gmail", note: "Client follow-up context" },
    { type: "google_drive", label: "Google Drive", note: "Contracts and tax docs" },
    { type: "manual_csv", label: "Manual CSV", note: "Invoices and expenses fallback" }
  ]
};

export function OnboardingView() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [userType, setUserType] = useState<UserType>("startup");
  const [selected, setSelected] = useState<string[]>(() => connectorOptions.startup.map((item) => item.type));
  const [status, setStatus] = useState<Record<string, string>>({});
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const options = useMemo(() => connectorOptions[userType], [userType]);

  function chooseUserType(next: UserType) {
    setUserType(next);
    setSelected(connectorOptions[next].map((item) => item.type));
    setStatus({});
    setSummary(null);
    setStep(1);
  }

  async function detectContext() {
    setLoading(true);
    setError(null);
    try {
      await ensureSession(userType);
      for (const type of selected) {
        setStatus((current) => ({ ...current, [type]: "connecting" }));
        const connector = await api.connect(type);
        setStatus((current) => ({ ...current, [type]: "syncing" }));
        if (connector.id) {
          await api.sync(connector.id);
        }
        setStatus((current) => ({ ...current, [type]: "synced" }));
      }
      setSummary(await api.dashboard());
      setStep(3);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to complete onboarding");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen finance-grid px-4 py-6">
      <div className="mx-auto max-w-6xl">
        <PageHeader eyebrow="Product onboarding" title="Set up your CFO operating context" />
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

        <div className="mb-5 grid gap-3 md:grid-cols-4">
          {["Choose profile", "Connect sources", "Verify context", "Enter app"].map((label, index) => (
            <div key={label} className={`rounded-lg border bg-card p-3 text-sm ${step === index + 1 ? "ring-2 ring-primary" : ""}`}>
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Step {index + 1}</div>
              <div className="mt-1 font-medium">{label}</div>
            </div>
          ))}
        </div>

        {step === 1 ? (
          <div className="grid gap-5 lg:grid-cols-[380px_1fr]">
            <Card>
              <CardHeader className="border-b">
                <CardTitle>User type</CardTitle>
              </CardHeader>
              <CardContent className="space-y-5 pt-5">
                <SegmentedControl value={userType} onChange={chooseUserType} items={[{ value: "startup", label: "Startup" }, { value: "freelancer", label: "Freelancer" }]} />
                <div className="rounded-lg bg-primary p-4 text-primary-foreground">
                  {userType === "startup" ? <Building2 className="mb-3 size-5" /> : <UserRoundCog className="mb-3 size-5" />}
                  <div className="text-sm font-semibold">
                    {userType === "startup" ? "Founder command center" : "Freelancer / agency OS"}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-primary-foreground/80">
                    {userType === "startup"
                      ? "Runway, burn, fundraising timing, vendor waste, and hiring decisions."
                      : "Receivables, cash gaps, tax reserve estimates, and follow-up drafts."}
                  </p>
                </div>
                <Button className="w-full" onClick={() => setStep(2)}>Continue</Button>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="border-b">
                <CardTitle>What clariFi will monitor</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3 pt-5 md:grid-cols-2">
                {(userType === "startup"
                  ? ["Runway changes", "Burn composition", "Fundraising timing", "Hiring impact", "Vendor waste", "Receivable pressure"]
                  : ["Overdue invoices", "Follow-up priority", "Cash gap risk", "Tax reserve", "Client profitability", "Recurring spend"]
                ).map((item) => (
                  <div key={item} className="rounded-lg border bg-background p-4 text-sm font-medium">{item}</div>
                ))}
              </CardContent>
            </Card>
          </div>
        ) : null}

        {step === 2 ? (
          <Card>
            <CardHeader className="border-b">
              <div className="flex items-center justify-between gap-4">
                <CardTitle>Choose data sources</CardTitle>
                <Badge variant="outline">Mock adapters, real boundaries</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-5 pt-5">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {options.map((connector) => {
                  const enabled = selected.includes(connector.type);
                  return (
                    <button
                      key={connector.type}
                      type="button"
                      onClick={() => setSelected((items) => enabled ? items.filter((item) => item !== connector.type) : [...items, connector.type])}
                      className={`rounded-lg border bg-background p-4 text-left transition hover:border-primary ${enabled ? "border-primary shadow-sm" : ""}`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="font-medium">{connector.label}</div>
                        {status[connector.type] === "synced" ? <CheckCircle2 className="size-4 text-primary" /> : <Badge variant="outline">{status[connector.type] ?? (enabled ? "selected" : "optional")}</Badge>}
                      </div>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">{connector.note}</p>
                    </button>
                  );
                })}
              </div>
              <div className="flex justify-between gap-3">
                <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
                <Button onClick={detectContext} disabled={loading || selected.length === 0}>
                  <PlugZap className="size-4" />
                  {loading ? "Detecting context..." : "Connect and detect context"}
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : null}

        {step === 3 && summary ? (
          <Card>
            <CardHeader className="border-b">
              <CardTitle className="flex items-center gap-2">
                <DatabaseZap className="size-4" />
                Sample financial context detected
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5 pt-5">
              <div className="grid gap-3 md:grid-cols-4">
                <Metric label="Cash" value={formatINR(summary.metrics.current_cash)} />
                <Metric label="Monthly burn" value={formatINR(summary.metrics.monthly_burn)} />
                <Metric label="Runway" value={`${formatNumber(summary.metrics.runway_months, 1)} mo`} />
                <Metric label="Overdue" value={formatINR(summary.metrics.overdue_receivables)} />
              </div>
              <div className="rounded-lg border bg-background p-4">
                <div className="text-sm font-semibold">Detected operating posture</div>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  clariFi has seeded organization-specific facts, calculated the financial truth layer, and generated CFO feed items from deterministic engines.
                </p>
              </div>
              <div className="flex justify-end">
                <Button onClick={() => router.push("/dashboard")}>Enter app</Button>
              </div>
            </CardContent>
          </Card>
        ) : null}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-background p-4">
      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{label}</div>
      <div className="mt-2 text-xl font-semibold">{value}</div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { Calculator, CreditCard, Scissors, UserPlus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { formatINR, formatNumber } from "@/lib/utils";
import { api } from "@/services/api";
import { PageHeader } from "@/features/shell/page-header";

type SimulationResult = Record<string, unknown> | null;

export function SimulationView({ mode = "all" }: { mode?: "all" | "hiring" | "vendors" | "cash-gap" }) {
  const [role, setRole] = useState("Engineer");
  const [baseSalary, setBaseSalary] = useState(180000);
  const [benefitsMultiplier, setBenefitsMultiplier] = useState(1.18);
  const [equipmentCost, setEquipmentCost] = useState(120000);
  const [softwareSeatCost, setSoftwareSeatCost] = useState(12000);
  const [onboardingCost, setOnboardingCost] = useState(50000);
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));
  const [vendorName, setVendorName] = useState("OpenAI duplicate workspace");
  const [vendorSavings, setVendorSavings] = useState(25000);
  const [cancellationDate, setCancellationDate] = useState(new Date().toISOString().slice(0, 10));
  const [riskNote, setRiskNote] = useState("Confirm no production workflow depends on this workspace before cancellation.");
  const [paymentDate, setPaymentDate] = useState(new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10));
  const [probability, setProbability] = useState(0.75);
  const [result, setResult] = useState<SimulationResult>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(label: string, fn: () => Promise<Record<string, unknown>>) {
    setLoading(label);
    setError(null);
    try {
      setResult(await fn());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setLoading(null);
    }
  }

  const showHiring = mode === "all" || mode === "hiring";
  const showVendors = mode === "all" || mode === "vendors";
  const showInvoices = mode === "all" || mode === "cash-gap";

  return (
    <>
      <PageHeader eyebrow="Runway simulator" title="Before/after finance decisions" />
      {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      <div className="grid gap-5 xl:grid-cols-[460px_1fr]">
        <div className="space-y-4">
          {showHiring ? (
            <Card>
              <CardHeader className="border-b">
                <CardTitle className="flex items-center gap-2">
                  <UserPlus className="size-4" />
                  Hire employee
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 pt-5">
                <div className="grid gap-3 md:grid-cols-2">
                  <Field label="Role" value={role} onChange={setRole} />
                  <NumberField label="Base salary / month" value={baseSalary} onChange={setBaseSalary} />
                  <NumberField label="Taxes/benefits multiplier" value={benefitsMultiplier} onChange={setBenefitsMultiplier} step="0.01" />
                  <NumberField label="Software seat / month" value={softwareSeatCost} onChange={setSoftwareSeatCost} />
                  <NumberField label="Equipment cost" value={equipmentCost} onChange={setEquipmentCost} />
                  <NumberField label="Recruiting/onboarding" value={onboardingCost} onChange={setOnboardingCost} />
                </div>
                <Field label="Start date" value={startDate} onChange={setStartDate} type="date" />
                <Button className="w-full" disabled={loading !== null} onClick={() => run("hiring", () => api.simulateHiring({
                  role,
                  monthly_cost: baseSalary,
                  benefits_multiplier: benefitsMultiplier,
                  equipment_cost: equipmentCost,
                  software_seat_cost: softwareSeatCost,
                  recruiting_onboarding_cost: onboardingCost,
                  start_date: startDate
                }))}>
                  <Calculator className="size-4" />
                  {loading === "hiring" ? "Simulating..." : "Simulate hire"}
                </Button>
              </CardContent>
            </Card>
          ) : null}

          {showVendors ? (
            <Card>
              <CardHeader className="border-b">
                <CardTitle className="flex items-center gap-2">
                  <Scissors className="size-4" />
                  Cut vendor
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 pt-5">
                <Field label="Vendor" value={vendorName} onChange={setVendorName} />
                <NumberField label="Monthly cost to remove" value={vendorSavings} onChange={setVendorSavings} />
                <Field label="Cancellation date" value={cancellationDate} onChange={setCancellationDate} type="date" />
                <div>
                  <label className="text-sm font-medium">Operational risk note</label>
                  <Textarea value={riskNote} onChange={(event) => setRiskNote(event.target.value)} />
                </div>
                <Button variant="outline" className="w-full" disabled={loading !== null} onClick={() => run("vendor", () => api.simulateVendorCut({
                  vendor_name: vendorName,
                  monthly_savings: vendorSavings,
                  cancellation_date: cancellationDate,
                  operational_risk_note: riskNote
                }))}>
                  {loading === "vendor" ? "Simulating..." : "Simulate vendor cut"}
                </Button>
              </CardContent>
            </Card>
          ) : null}

          {showInvoices ? (
            <Card>
              <CardHeader className="border-b">
                <CardTitle className="flex items-center gap-2">
                  <CreditCard className="size-4" />
                  Collect invoice
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 pt-5">
                <Field label="Expected payment date" value={paymentDate} onChange={setPaymentDate} type="date" />
                <NumberField label="Collection probability" value={probability} onChange={setProbability} step="0.05" />
                <Button variant="outline" className="w-full" disabled={loading !== null} onClick={() => run("invoice", () => api.simulateInvoiceCollection({
                  expected_payment_date: paymentDate,
                  probability
                }))}>
                  {loading === "invoice" ? "Simulating..." : "Simulate collection"}
                </Button>
              </CardContent>
            </Card>
          ) : null}
        </div>

        <Card className="min-h-[520px]">
          <CardHeader className="border-b">
            <CardTitle>Deterministic result</CardTitle>
          </CardHeader>
          <CardContent className="pt-5">
            {!result ? (
              <div className="rounded-lg border bg-background p-8 text-sm text-muted-foreground">
                Choose a scenario to calculate runway, burn, and cash impact. Results come from deterministic engines only.
              </div>
            ) : (
              <SimulationResultView result={result} />
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}

function SimulationResultView({ result }: { result: Record<string, unknown> }) {
  const scalarEntries = Object.entries(result).filter(([key, value]) => !["evidence", "formula", "engine_name", "engine_version"].includes(key) && typeof value !== "object");
  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-2">
        {scalarEntries.map(([key, value]) => (
          <Result key={key} label={key.replaceAll("_", " ")} value={formatValue(key, value)} />
        ))}
      </div>
      <div className="rounded-lg bg-primary p-4 text-primary-foreground">
        <div className="text-sm font-semibold">Verified scenario output</div>
        <p className="mt-2 text-sm leading-6 text-primary-foreground/80">
          The output uses current financial facts plus scenario inputs. No model-generated arithmetic is used.
        </p>
      </div>
      {Array.isArray(result.evidence) ? (
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Evidence</div>
          {(result.evidence as { title?: string; excerpt?: string }[]).map((item, index) => (
            <div key={index} className="rounded-md border bg-background p-3 text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{item.title}</span>
              <p className="mt-1 leading-6">{item.excerpt}</p>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return (
    <div>
      <label className="text-sm font-medium">{label}</label>
      <Input type={type} value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}

function NumberField({ label, value, onChange, step = "1000" }: { label: string; value: number; onChange: (value: number) => void; step?: string }) {
  return (
    <div>
      <label className="text-sm font-medium">{label}</label>
      <Input type="number" step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </div>
  );
}

function Result({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-background p-4">
      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{label}</div>
      <div className="mt-2 text-lg font-semibold">{value}</div>
    </div>
  );
}

function formatValue(key: string, value: unknown) {
  if (typeof value === "number") {
    if (key.includes("runway")) return `${formatNumber(value, 2)} mo`;
    if (key.includes("probability") || key.includes("multiplier")) return formatNumber(value, 2);
    if (key.includes("risk")) return String(value);
    return formatINR(value);
  }
  if (typeof value === "string" && /^-?\d+(\.\d+)?$/.test(value)) {
    const numeric = Number(value);
    if (key.includes("runway")) return `${formatNumber(numeric, 2)} mo`;
    if (key.includes("probability") || key.includes("multiplier")) return formatNumber(numeric, 2);
    return formatINR(numeric);
  }
  return String(value);
}

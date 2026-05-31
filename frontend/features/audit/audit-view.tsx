"use client";

import { useState } from "react";
import { FileClock, ShieldCheck, Workflow } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SegmentedControl } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/hooks/use-api";
import { api } from "@/services/api";
import { PageHeader } from "@/features/shell/page-header";
import type { AuditLog } from "@/types/api";

export function AuditView() {
  const [mode, setMode] = useState<"user" | "developer">("user");
  const audit = useResource(api.audit, []);
  const workflows = useResource(api.workflowRuns, []);

  return (
    <>
      <PageHeader eyebrow="Audit trail" title={mode === "user" ? "Why clariFi said this" : "Raw workflow replay"}>
        <SegmentedControl value={mode} onChange={setMode} items={[{ value: "user", label: "User view" }, { value: "developer", label: "Developer view" }]} />
      </PageHeader>
      {mode === "user" ? (
        audit.loading ? <Skeleton className="h-96" /> : (
          <div className="space-y-3">
            {audit.data?.length === 0 ? <div className="rounded-lg border bg-card p-6 text-sm text-muted-foreground">No audit logs yet.</div> : null}
            {audit.data?.map((log) => <UserAuditCard key={log.id} log={log} />)}
          </div>
        )
      ) : (
        <div className="grid gap-5 xl:grid-cols-2">
          <div className="space-y-3">
            <h2 className="font-display text-xl font-semibold">Audit logs</h2>
            {audit.loading ? <Skeleton className="h-96" /> : audit.data?.map((log) => (
              <Card key={log.id}>
                <CardHeader className="border-b">
                  <div className="flex items-center justify-between gap-3">
                    <CardTitle className="flex items-center gap-2">
                      <FileClock className="size-4" />
                      {log.action}
                    </CardTitle>
                    <Badge variant="outline">{log.verification_status}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="grid gap-4 pt-5">
                  <pre className="max-h-56 overflow-auto rounded-md bg-background p-3 text-xs">{JSON.stringify(log.inputs, null, 2)}</pre>
                  <pre className="max-h-56 overflow-auto rounded-md bg-background p-3 text-xs">{JSON.stringify(log.outputs, null, 2)}</pre>
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="space-y-3">
            <h2 className="font-display text-xl font-semibold">Workflow runs</h2>
            {workflows.loading ? <Skeleton className="h-96" /> : workflows.data?.map((run) => (
              <Card key={run.id}>
                <CardHeader className="border-b">
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      <Workflow className="size-4" />
                      {run.workflow_name}
                    </CardTitle>
                    <Badge variant="outline">{run.status}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2 pt-5">
                  {run.steps.map((step) => (
                    <div key={step.id} className="rounded-md border bg-background p-3">
                      <div className="text-sm font-semibold">{step.step_name}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{step.duration_ms ?? 0} ms · {step.status}</div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function UserAuditCard({ log }: { log: AuditLog }) {
  const context = readObject(log.inputs?.context_pack);
  const outputs = readObject(log.outputs);
  const verification = readObject(outputs?.verification);
  const facts = Array.isArray(context?.source_fact_ids) ? context.source_fact_ids : [];
  const answer = typeof outputs?.answer === "string" ? outputs.answer : typeof outputs?.status === "string" ? `Status changed to ${outputs.status}` : log.action;

  return (
    <Card>
      <CardHeader className="border-b">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="size-4" />
              {friendlyAction(log.action)}
            </CardTitle>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{answer}</p>
          </div>
          <Badge variant={log.verification_status?.includes("verified") || log.verification_status?.includes("approved") ? "default" : "outline"}>
            {log.verification_status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4 pt-5 md:grid-cols-2">
        <AuditFact label="Facts used" value={facts.length ? facts.join(", ") : "Source facts recorded in calculation logs"} />
        <AuditFact label="Formulas used" value={summarizeFormulas(context)} />
        <AuditFact label="Source records" value={summarizeSourceRecords(context)} />
        <AuditFact label="AI model/template" value={`${log.model_used ?? "not used"} · ${log.prompt_version ?? "no prompt"}`} />
        <AuditFact label="Verification" value={typeof verification?.reason === "string" ? verification.reason : log.verification_status} />
        <AuditFact label="Created" value={new Date(log.created_at).toLocaleString()} />
      </CardContent>
    </Card>
  );
}

function AuditFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-background p-3">
      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{label}</div>
      <p className="mt-2 text-sm leading-6">{value}</p>
    </div>
  );
}

function friendlyAction(action: string) {
  if (action.includes("cfo_chat")) return "CFO Chat answer";
  if (action.includes("recommendation.approve")) return "Recommendation approved";
  if (action.includes("recommendation.dismiss")) return "Recommendation dismissed";
  if (action.includes("follow_up")) return "Follow-up draft saved";
  if (action.includes("calculate")) return "Financial calculation";
  return action;
}

function summarizeFormulas(context: Record<string, unknown> | null) {
  if (!context) return "No context pack attached.";
  const containers = ["runway", "burn_rate", "receivables", "cash_position"] as const;
  const formulas: string[] = [];
  for (const container of containers) {
    const value = readObject(context[container]);
    for (const item of Object.values(value ?? {})) {
      const obj = readObject(item);
      if (typeof obj?.formula === "string") formulas.push(obj.formula);
    }
  }
  return formulas.length ? [...new Set(formulas)].join("; ") : "Formula references are available in raw calculation logs.";
}

function summarizeSourceRecords(context: Record<string, unknown> | null) {
  if (!context) return "No context pack attached.";
  const ids: string[] = [];
  const collect = (value: unknown) => {
    if (Array.isArray(value)) value.forEach(collect);
    else if (value && typeof value === "object") {
      const obj = value as Record<string, unknown>;
      if (Array.isArray(obj.source_record_ids)) ids.push(...obj.source_record_ids.map(String));
      Object.values(obj).forEach(collect);
    }
  };
  collect(context);
  return ids.length ? [...new Set(ids)].slice(0, 12).join(", ") : "No source records attached to this audit item.";
}

function readObject(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

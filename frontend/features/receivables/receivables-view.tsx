"use client";

import { Copy, MailPlus, RefreshCw, Send } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { SegmentedControl } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useResource } from "@/hooks/use-api";
import { formatINR } from "@/lib/utils";
import { api } from "@/services/api";
import { PageHeader } from "@/features/shell/page-header";
import type { Action, Feed, ReceivableInvoice } from "@/types/api";

type ReceivablesData = {
  invoices: ReceivableInvoice[];
  feed: Feed;
};

type Tone = "polite" | "firm" | "final_notice";

export function ReceivablesView({ mode = "receivables" }: { mode?: "receivables" | "follow-ups" }) {
  const [version, setVersion] = useState(0);
  const [selectedInvoice, setSelectedInvoice] = useState<ReceivableInvoice | null>(null);
  const [notice, setNotice] = useState<{ tone: "success" | "error"; message: string } | null>(null);
  const { data, loading, error, setData } = useResource<ReceivablesData>(async () => {
    const [invoices, feed] = await Promise.all([api.receivables(), api.feed()]);
    return { invoices, feed };
  }, [version]);

  async function runReceivablesWorkflow() {
    setNotice(null);
    try {
      await api.runReceivables();
      setVersion((value) => value + 1);
      setNotice({ tone: "success", message: "Receivables workflow completed and draft actions refreshed." });
    } catch (err) {
      setNotice({ tone: "error", message: err instanceof Error ? err.message : "Unable to run receivables workflow." });
    }
  }

  function upsertAction(action: Action) {
    setData((current) => current ? {
      ...current,
      feed: {
        ...current.feed,
        actions: [action, ...current.feed.actions.filter((item) => item.id !== action.id)]
      }
    } : current);
  }

  if (loading) return <Skeleton className="h-[560px]" />;
  if (error) return <div className="rounded-lg border bg-card p-6 text-sm text-red-700">{error}</div>;
  if (!data) return null;

  const draftActions = data.feed.actions.filter((action) => action.action_type === "email_draft");

  return (
    <>
      <PageHeader eyebrow={mode === "follow-ups" ? "Follow-up desk" : "Receivables agent"} title={mode === "follow-ups" ? "Drafts waiting for approval" : "Unpaid invoices and cash impact"}>
        <Button onClick={runReceivablesWorkflow}>
          <MailPlus className="size-4" />
          Draft follow-ups
        </Button>
      </PageHeader>
      {notice ? (
        <div className={`mb-4 rounded-lg border p-3 text-sm ${notice.tone === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-red-200 bg-red-50 text-red-700"}`}>
          {notice.message}
        </div>
      ) : null}
      <div className="grid gap-5 xl:grid-cols-[1fr_400px]">
        <div className="space-y-4">
          {mode === "receivables" ? (
            data.invoices.length === 0 ? (
              <div className="rounded-lg border bg-card p-6 text-sm text-muted-foreground">No receivable invoices found.</div>
            ) : (
              data.invoices.map((invoice) => (
                <Card key={invoice.id}>
                  <CardHeader className="border-b">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <CardTitle>{invoice.customer_name}</CardTitle>
                        <p className="mt-1 text-sm text-muted-foreground">{invoice.invoice_number} · due {invoice.due_on}</p>
                      </div>
                      <Badge variant={invoice.priority === "high" ? "danger" : "warning"}>{invoice.priority}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4 pt-5">
                    <div className="grid gap-3 md:grid-cols-3">
                      <Fact label="Amount owed" value={formatINR(invoice.amount - invoice.paid_amount)} />
                      <Fact label="Days overdue" value={`${invoice.days_overdue}`} />
                      <Fact label="Status" value={invoice.status} />
                    </div>
                    <div className="rounded-md border bg-background p-3 text-sm text-muted-foreground">
                      Suggested action: {invoice.suggested_action}. Expected cash impact is {formatINR(invoice.amount - invoice.paid_amount)} if collected.
                    </div>
                    <Button variant="outline" onClick={() => setSelectedInvoice(invoice)}>
                      <MailPlus className="size-4" />
                      Draft follow-up
                    </Button>
                  </CardContent>
                </Card>
              ))
            )
          ) : (
            draftActions.length === 0 ? (
              <div className="rounded-lg border bg-card p-6 text-sm text-muted-foreground">No saved follow-up drafts yet.</div>
            ) : (
              draftActions.map((action) => <DraftActionCard key={action.id} action={action} onUpdate={upsertAction} />)
            )
          )}
        </div>

        <Card>
          <CardHeader className="border-b">
            <CardTitle>Saved follow-up drafts</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-5">
            {draftActions.length === 0 ? <p className="text-sm text-muted-foreground">Drafts created by the modal or workflow appear here.</p> : null}
            {draftActions.map((action) => (
              <div key={action.id} className="rounded-md border bg-background p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-semibold">{action.title}</div>
                  <Badge variant="outline">{action.status}</Badge>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">{String(action.payload.invoice_number ?? "")} · {String(action.payload.tone ?? "polite")}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {selectedInvoice ? (
        <DraftModal
          invoice={selectedInvoice}
          onClose={() => setSelectedInvoice(null)}
          onSaved={(action) => {
            upsertAction(action);
            setSelectedInvoice(null);
            setNotice({ tone: "success", message: "Follow-up draft saved as an approval-required action." });
          }}
        />
      ) : null}
    </>
  );
}

function DraftModal({ invoice, onClose, onSaved }: { invoice: ReceivableInvoice; onClose: () => void; onSaved: (action: Action) => void }) {
  const [tone, setTone] = useState<Tone>("polite");
  const [to, setTo] = useState(invoice.customer_email ?? "");
  const [subject, setSubject] = useState(`Follow-up on invoice ${invoice.invoice_number}`);
  const [body, setBody] = useState(defaultBody(invoice, "polite"));
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    setBody(defaultBody(invoice, tone));
  }, [invoice, tone]);

  async function saveDraft() {
    setLoading(true);
    setNotice(null);
    try {
      onSaved(await api.createFollowUpDraft({ invoice_id: invoice.id, tone, to, subject, body }));
    } finally {
      setLoading(false);
    }
  }

  async function copy() {
    await navigator.clipboard.writeText(`To: ${to}\nSubject: ${subject}\n\n${body}`);
    setNotice("Draft copied to clipboard.");
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/20 p-4 backdrop-blur-sm">
      <Card className="w-full max-w-2xl shadow-xl">
        <CardHeader className="border-b">
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle>Draft invoice follow-up</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                {invoice.invoice_number} · {formatINR(invoice.amount - invoice.paid_amount)} · due {invoice.due_on}
              </p>
            </div>
            <Button variant="ghost" onClick={onClose}>Close</Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 pt-5">
          {notice ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-2 text-sm text-emerald-800">{notice}</div> : null}
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="To" value={to} onChange={setTo} />
            <Field label="Invoice number" value={invoice.invoice_number} onChange={() => undefined} disabled />
            <Field label="Amount" value={formatINR(invoice.amount - invoice.paid_amount)} onChange={() => undefined} disabled />
            <Field label="Due date" value={invoice.due_on} onChange={() => undefined} disabled />
          </div>
          <div>
            <label className="text-sm font-medium">Tone</label>
            <div className="mt-2">
              <SegmentedControl<Tone> value={tone} onChange={setTone} items={[{ value: "polite", label: "Polite" }, { value: "firm", label: "Firm" }, { value: "final_notice", label: "Final notice" }]} />
            </div>
          </div>
          <Field label="Subject" value={subject} onChange={setSubject} />
          <div>
            <label className="text-sm font-medium">Email body</label>
            <Textarea value={body} onChange={(event) => setBody(event.target.value)} className="min-h-[220px]" />
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="outline" onClick={copy}>
              <Copy className="size-4" />
              Copy
            </Button>
            <Button variant="outline" onClick={saveDraft} disabled={loading}>
              Save draft action
            </Button>
            <Button onClick={async () => {
              const action = await api.createFollowUpDraft({ invoice_id: invoice.id, tone, to, subject, body });
              const sent = await api.markActionSent(action.id);
              onSaved(sent);
            }} disabled={loading}>
              <Send className="size-4" />
              Mark as sent
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function DraftActionCard({ action, onUpdate }: { action: Action; onUpdate: (action: Action) => void }) {
  return (
    <Card>
      <CardHeader className="border-b">
        <div className="flex items-start justify-between">
          <CardTitle>{action.title}</CardTitle>
          <Badge variant="outline">{action.status}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 pt-5">
        <div className="rounded-md border bg-background p-3 text-sm">
          <div className="font-medium">{String(action.payload.subject ?? "")}</div>
          <pre className="mt-3 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">{String(action.payload.body ?? "")}</pre>
        </div>
        <Button variant="outline" onClick={() => api.markActionSent(action.id).then(onUpdate)} disabled={action.status === "sent"}>
          <Send className="size-4" />
          Mark as sent
        </Button>
      </CardContent>
    </Card>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-background p-3">
      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{label}</div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  );
}

function Field({ label, value, onChange, disabled = false }: { label: string; value: string; onChange: (value: string) => void; disabled?: boolean }) {
  return (
    <div>
      <label className="text-sm font-medium">{label}</label>
      <Input value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}

function defaultBody(invoice: ReceivableInvoice, tone: Tone) {
  const opener = {
    polite: "I hope you are doing well. I wanted to gently follow up",
    firm: "I am following up again",
    final_notice: "This is a final reminder before we escalate internally"
  }[tone];
  return `Hi ${invoice.customer_name},\n\n${opener} on invoice ${invoice.invoice_number} for ${formatINR(invoice.amount - invoice.paid_amount)}, due on ${invoice.due_on}. Could you confirm the expected payment date?\n\nRegards`;
}

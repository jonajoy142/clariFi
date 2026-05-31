"use client";

import { RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/hooks/use-api";
import { api } from "@/services/api";
import { PageHeader } from "@/features/shell/page-header";
import type { Recommendation } from "@/types/api";
import { RecommendationCard } from "./recommendation-card";

export function FeedView() {
  const [version, setVersion] = useState(0);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ tone: "success" | "error"; message: string } | null>(null);
  const { data, loading, error, setData } = useResource(api.feed, [version]);

  async function refreshBriefing() {
    setNotice(null);
    try {
      await api.runFinancialAnalysis();
      setVersion((value) => value + 1);
      setNotice({ tone: "success", message: "Briefing refreshed from deterministic workflow." });
    } catch (err) {
      setNotice({ tone: "error", message: err instanceof Error ? err.message : "Unable to refresh briefing." });
    }
  }

  async function transition(rec: Recommendation, status: "approved" | "dismissed") {
    setBusyId(rec.id);
    setNotice(null);
    try {
      const updated = status === "approved" ? await api.approveRecommendation(rec.id) : await api.dismissRecommendation(rec.id);
      setData((current) => current ? {
        ...current,
        recommendations: current.recommendations.map((item) => item.id === updated.id ? updated : item)
      } : current);
      setNotice({ tone: "success", message: status === "approved" ? "Recommendation moved to Approved actions." : "Recommendation moved to Dismissed." });
    } catch (err) {
      setNotice({ tone: "error", message: err instanceof Error ? err.message : "Unable to update recommendation." });
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <Skeleton className="h-[620px]" />;
  if (error) return <div className="rounded-lg border bg-card p-6 text-sm text-red-700">{error}</div>;
  if (!data) return null;

  const active = data.recommendations.filter((rec) => rec.status === "active" || rec.status === "open");
  const approved = data.recommendations.filter((rec) => rec.status === "approved");
  const dismissed = data.recommendations.filter((rec) => rec.status === "dismissed");

  return (
    <>
      <PageHeader eyebrow="CFO feed" title="Risks, evidence, and actions">
        <Button onClick={refreshBriefing}>
          <RefreshCw className="size-4" />
          Refresh briefing
        </Button>
      </PageHeader>
      {notice ? (
        <div className={`mb-4 rounded-lg border p-3 text-sm ${notice.tone === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-red-200 bg-red-50 text-red-700"}`}>
          {notice.message}
        </div>
      ) : null}
      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <RecommendationSection title="Active CFO decisions" empty="No active CFO recommendations right now. Refresh the briefing to rerun analysis.">
            {active.map((recommendation) => (
              <RecommendationCard
                key={recommendation.id}
                recommendation={recommendation}
                busy={busyId === recommendation.id}
                onApprove={() => transition(recommendation, "approved")}
                onDismiss={() => transition(recommendation, "dismissed")}
              />
            ))}
          </RecommendationSection>
          <RecommendationSection title="Approved actions" empty="Approved recommendations will move here and stay here after refresh.">
            {approved.map((recommendation) => (
              <RecommendationCard key={recommendation.id} recommendation={recommendation} />
            ))}
          </RecommendationSection>
          <RecommendationSection title="Dismissed" empty="Dismissed recommendations will move here and stay dismissed after refresh.">
            {dismissed.map((recommendation) => (
              <RecommendationCard key={recommendation.id} recommendation={recommendation} />
            ))}
          </RecommendationSection>
        </div>
        <div className="space-y-4">
          <Card>
            <CardHeader className="border-b">
              <CardTitle>Alerts</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 pt-5">
              {data.alerts.length === 0 ? <p className="text-sm text-muted-foreground">No open alerts.</p> : null}
              {data.alerts.map((alert) => (
                <div key={alert.id} className="rounded-md border bg-background p-3">
                  <div className="text-sm font-semibold">{alert.title}</div>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">{alert.message}</p>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="border-b">
              <CardTitle>Draft actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 pt-5">
              {data.actions.length === 0 ? <p className="text-sm text-muted-foreground">No draft actions yet.</p> : null}
              {data.actions.map((action) => (
                <div key={action.id} className="rounded-md border bg-background p-3">
                  <div className="text-sm font-semibold">{action.title}</div>
                  <p className="mt-1 text-xs text-muted-foreground">{action.action_type} · {action.status}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}

function RecommendationSection({ title, empty, children }: { title: string; empty: string; children: ReactNode }) {
  const childArray = Array.isArray(children) ? children : [children];
  const hasChildren = childArray.some(Boolean);
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-semibold">{title}</h2>
      </div>
      {hasChildren ? children : <div className="rounded-lg border bg-card p-6 text-sm text-muted-foreground">{empty}</div>}
    </section>
  );
}

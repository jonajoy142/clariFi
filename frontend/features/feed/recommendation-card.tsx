"use client";

import Link from "next/link";
import { Check, ExternalLink, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatINR } from "@/lib/utils";
import type { Recommendation } from "@/types/api";

export function RecommendationCard({
  recommendation,
  busy,
  onApprove,
  onDismiss
}: {
  recommendation: Recommendation;
  busy?: boolean;
  onApprove?: () => void;
  onDismiss?: () => void;
}) {
  const active = recommendation.status === "active" || recommendation.status === "open";
  return (
    <Card className={active ? "" : "opacity-88"}>
      <CardHeader className="border-b">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge variant={active ? "default" : "outline"}>{recommendation.status}</Badge>
              <span className="text-xs text-muted-foreground">{Math.round((recommendation.confidence ?? recommendation.confidence_score) * 100)}% confidence</span>
            </div>
            <CardTitle className="text-base">{recommendation.title}</CardTitle>
          </div>
          {recommendation.impact_amount ?? recommendation.financial_impact_amount ? (
            <Badge>{formatINR(recommendation.impact_amount ?? recommendation.financial_impact_amount)}</Badge>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-5">
        <Section label="What happened" value={recommendation.description ?? recommendation.issue} />
        <Section label="Why it matters" value={recommendation.issue} />
        <Section label="Exact financial impact" value={recommendation.impact} />
        <Section label="Recommended action" value={recommendation.recommended_action} />
        <div className="rounded-md border bg-background p-3">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Evidence
            <ExternalLink className="size-3" />
          </div>
          <div className="space-y-2">
            {recommendation.evidence.length === 0 ? <p className="text-sm text-muted-foreground">No additional evidence attached.</p> : null}
            {recommendation.evidence.map((item, index) => (
              <p key={`${item.source_id}-${index}`} className="text-sm leading-6 text-muted-foreground">{item.excerpt}</p>
            ))}
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
          <div className="flex gap-2">
            <Button onClick={onApprove} disabled={!active || busy}>
              <Check className="size-4" />
              {busy ? "Updating..." : recommendation.primary_cta ?? "Approve"}
            </Button>
            <Button variant="outline" onClick={onDismiss} disabled={!active || busy}>
              <X className="size-4" />
              {recommendation.secondary_cta ?? "Dismiss"}
            </Button>
          </div>
          {recommendation.audit_log_id ? (
            <Button variant="ghost" asChild>
              <Link href="/audit">
                Audit link
                <ExternalLink className="size-4" />
              </Link>
            </Button>
          ) : (
            <Badge variant="outline">Audit linked via facts</Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function Section({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{label}</div>
      <p className="mt-1 text-sm leading-6">{value || "Not provided"}</p>
    </div>
  );
}

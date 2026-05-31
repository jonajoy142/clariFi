"use client";

import { RefreshCw } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/hooks/use-api";
import { api } from "@/services/api";
import { PageHeader } from "@/features/shell/page-header";
import type { Connector } from "@/types/api";

const labels: Record<string, string> = {
  not_connected: "Not connected",
  disconnected: "Not connected",
  mock_connected: "Mock connected",
  syncing: "Syncing",
  connected: "Connected",
  error: "Error",
  failed: "Error",
  coming_soon: "Coming soon"
};

export function IntegrationsView() {
  const [version, setVersion] = useState(0);
  const [busyType, setBusyType] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const { data, loading, error } = useResource(api.connectors, [version]);

  async function connectAndSync(connector: Connector) {
    if (connector.status === "coming_soon") return;
    setBusyType(connector.type);
    setNotice(null);
    try {
      const connected = connector.id ? connector : await api.connect(connector.type);
      if (connected.id) {
        await api.sync(connected.id);
      }
      setNotice(`${connector.display_name ?? connector.type} synced through mock adapter.`);
      setVersion((value) => value + 1);
    } finally {
      setBusyType(null);
    }
  }

  if (loading) return <Skeleton className="h-96" />;
  if (error) return <div className="rounded-lg border bg-card p-6 text-sm text-red-700">{error}</div>;

  return (
    <>
      <PageHeader eyebrow="Settings" title="Integrations and sync state" />
      {notice ? <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div> : null}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data?.map((connector) => {
          const disabled = connector.status === "coming_soon" || busyType === connector.type;
          return (
            <Card key={connector.type}>
              <CardHeader className="border-b">
                <div className="flex items-center justify-between gap-3">
                  <CardTitle>{connector.display_name ?? connector.type.replace("_", " ")}</CardTitle>
                  <Badge variant={connector.status === "connected" ? "default" : connector.status === "coming_soon" ? "outline" : "warning"}>
                    {labels[connector.status] ?? connector.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 pt-5">
                <p className="text-sm leading-6 text-muted-foreground">{connector.description}</p>
                <div className="rounded-md border bg-background p-3 text-xs text-muted-foreground">
                  Mode: {connector.mode ?? "mock"} · Last sync: {connector.last_synced_at ? new Date(connector.last_synced_at).toLocaleString() : "never"}
                </div>
                <Button variant="outline" className="w-full" onClick={() => connectAndSync(connector)} disabled={disabled}>
                  <RefreshCw className="size-4" />
                  {busyType === connector.type ? "Syncing..." : connector.id ? "Sync now" : connector.status === "coming_soon" ? "Coming soon" : "Connect mock"}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </>
  );
}

import { IntegrationsView } from "@/features/integrations/integrations-view";
import { AppShell } from "@/features/shell/app-shell";

export default function IntegrationsPage() {
  return (
    <AppShell>
      <IntegrationsView />
    </AppShell>
  );
}

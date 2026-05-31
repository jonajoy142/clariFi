import { ClientProfitabilityView } from "@/features/client-profitability/client-profitability-view";
import { AppShell } from "@/features/shell/app-shell";

export default function ClientProfitabilityPage() {
  return (
    <AppShell>
      <ClientProfitabilityView />
    </AppShell>
  );
}

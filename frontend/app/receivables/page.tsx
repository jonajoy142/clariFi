import { ReceivablesView } from "@/features/receivables/receivables-view";
import { AppShell } from "@/features/shell/app-shell";

export default function ReceivablesPage() {
  return (
    <AppShell>
      <ReceivablesView />
    </AppShell>
  );
}

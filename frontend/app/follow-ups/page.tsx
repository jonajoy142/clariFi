import { AppShell } from "@/features/shell/app-shell";
import { ReceivablesView } from "@/features/receivables/receivables-view";

export default function FollowUpsPage() {
  return (
    <AppShell>
      <ReceivablesView mode="follow-ups" />
    </AppShell>
  );
}

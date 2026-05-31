import { AuditView } from "@/features/audit/audit-view";
import { AppShell } from "@/features/shell/app-shell";

export default function AuditPage() {
  return (
    <AppShell>
      <AuditView />
    </AppShell>
  );
}

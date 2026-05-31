import { AppShell } from "@/features/shell/app-shell";
import { SimulationView } from "@/features/simulation/simulation-view";

export default function CashGapPage() {
  return (
    <AppShell>
      <SimulationView mode="cash-gap" />
    </AppShell>
  );
}

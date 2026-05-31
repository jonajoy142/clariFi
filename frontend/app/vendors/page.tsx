import { AppShell } from "@/features/shell/app-shell";
import { SimulationView } from "@/features/simulation/simulation-view";

export default function VendorsPage() {
  return (
    <AppShell>
      <SimulationView mode="vendors" />
    </AppShell>
  );
}

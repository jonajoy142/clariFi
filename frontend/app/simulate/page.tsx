import { AppShell } from "@/features/shell/app-shell";
import { SimulationView } from "@/features/simulation/simulation-view";

export default function SimulatePage() {
  return (
    <AppShell>
      <SimulationView />
    </AppShell>
  );
}

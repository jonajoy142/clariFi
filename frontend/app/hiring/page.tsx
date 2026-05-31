import { AppShell } from "@/features/shell/app-shell";
import { SimulationView } from "@/features/simulation/simulation-view";

export default function HiringPage() {
  return (
    <AppShell>
      <SimulationView mode="hiring" />
    </AppShell>
  );
}

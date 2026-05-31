import { FeedView } from "@/features/feed/feed-view";
import { AppShell } from "@/features/shell/app-shell";

export default function FeedPage() {
  return (
    <AppShell>
      <FeedView />
    </AppShell>
  );
}

import { ChatView } from "@/features/chat/chat-view";
import { AppShell } from "@/features/shell/app-shell";

export default function ChatPage() {
  return (
    <AppShell>
      <ChatView />
    </AppShell>
  );
}

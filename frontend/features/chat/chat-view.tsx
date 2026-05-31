"use client";

import { FormEvent, useState } from "react";
import { Bot, CornerDownLeft, ShieldCheck, Wrench } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/features/shell/page-header";
import { api, currentUserType } from "@/services/api";
import type { ChatResponse } from "@/types/api";

const startupStarters = [
  "Can I hire one engineer at ₹1.8L/month?",
  "How many employees now?",
  "Break down cash burn into salaries vs other costs.",
  "Who owes me money?",
  "Do I need to start fundraising this week?",
  "What should I cut?"
];

const freelancerStarters = [
  "Who owes me money?",
  "Will I run out of cash if this client pays late?",
  "How much should I reserve for tax?",
  "Break down cash burn into salaries vs other costs."
];

export function ChatView() {
  const starters = currentUserType() === "freelancer" ? freelancerStarters : startupStarters;
  const [question, setQuestion] = useState(starters[0]);
  const [threadId, setThreadId] = useState<string | undefined>();
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; content: string; response?: ChatResponse }[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    const current = question.trim();
    setQuestion("");
    setMessages((items) => [...items, { role: "user", content: current }]);
    try {
      const response = await api.chat(current, threadId);
      setThreadId(response.thread_id);
      setMessages((items) => [...items, { role: "assistant", content: response.answer, response }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to answer with grounded tools");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <PageHeader eyebrow="Grounded CFO chat" title="Ask questions that call tools" />
      {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <Card className="min-h-[680px]">
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2">
              <Bot className="size-4" />
              CFO conversation
            </CardTitle>
          </CardHeader>
          <CardContent className="flex min-h-[600px] flex-col gap-4 pt-5">
            <div className="flex-1 space-y-4">
              {messages.length === 0 ? (
                <div className="rounded-lg border bg-background p-6 text-sm text-muted-foreground">
                  Every response is built from deterministic tool outputs, evidence retrieval, and numeric grounding checks.
                </div>
              ) : null}
              {messages.map((message, index) => (
                <div key={index} className={message.role === "user" ? "flex justify-end" : "flex justify-start"}>
                  <div className={message.role === "user" ? "max-w-[78%] rounded-lg bg-primary px-4 py-3 text-sm leading-6 text-primary-foreground" : "max-w-[86%] rounded-lg border bg-background px-4 py-3 text-sm leading-6"}>
                    {message.content}
                    {message.response ? (
                      <div className="mt-4 flex flex-wrap gap-2 border-t pt-3">
                        {message.response.tools_used.map((tool) => <Badge key={tool} variant="outline"><Wrench className="mr-1 size-3" />{tool}</Badge>)}
                        <Badge variant={message.response.verification.passed ? "default" : "danger"}>
                          <ShieldCheck className="mr-1 size-3" />
                          {message.response.verification.passed ? "verified" : "rejected"}
                        </Badge>
                      </div>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
            <form onSubmit={submit} className="border-t pt-4">
              <Textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about hiring, runway, receivables, fundraising, or vendor cuts..." />
              <div className="mt-3 flex items-center justify-between gap-3">
                <div className="hidden gap-2 lg:flex">
                  {starters.slice(0, 3).map((starter) => (
                    <button key={starter} type="button" onClick={() => setQuestion(starter)} className="rounded-full border bg-background px-3 py-1 text-xs text-muted-foreground hover:text-foreground">
                      {starter}
                    </button>
                  ))}
                </div>
                <Button disabled={loading}>
                  <CornerDownLeft className="size-4" />
                  Ask
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Evidence from last answer</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-5">
            {[...messages].reverse().find((message) => message.response)?.response?.evidence.map((item) => (
              <div key={item.source_id} className="rounded-md border bg-background p-3">
                <div className="text-sm font-semibold">{item.title}</div>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.excerpt}</p>
              </div>
            )) ?? <p className="text-sm text-muted-foreground">No evidence retrieved yet.</p>}
          </CardContent>
        </Card>
      </div>
    </>
  );
}

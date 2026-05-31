"use client";

import { useRouter } from "next/navigation";
import { Building2, BriefcaseBusiness, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { loginAs } from "@/services/api";
import type { UserType } from "@/types/api";

const demos: {
  userType: UserType;
  title: string;
  subtitle: string;
  bullets: string[];
}[] = [
  {
    userType: "startup",
    title: "Startup founder",
    subtitle: "Runway, burn, hiring, fundraising, vendors.",
    bullets: ["₹23L cash position", "AWS spend spike", "Hiring and fundraising decisions"]
  },
  {
    userType: "freelancer",
    title: "Freelancer / agency",
    subtitle: "Receivables, follow-ups, cash gap, tax reserve.",
    bullets: ["₹42K overdue invoice", "Draft follow-up workflow", "Tax reserve estimate"]
  }
];

export function LoginView() {
  const router = useRouter();
  const [loading, setLoading] = useState<UserType | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function selectDemo(userType: UserType) {
    setLoading(userType);
    setError(null);
    try {
      await loginAs(userType);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start demo session");
    } finally {
      setLoading(null);
    }
  }

  return (
    <main className="min-h-screen finance-grid px-4 py-8">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl items-center">
        <div className="grid w-full gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <section className="rounded-2xl border bg-primary p-8 text-primary-foreground shadow-sm">
            <div className="flex size-11 items-center justify-center rounded-xl bg-primary-foreground/10">
              <span className="font-display text-lg font-semibold">cf</span>
            </div>
            <h1 className="mt-8 font-display text-5xl font-semibold tracking-tight">clariFi</h1>
            <p className="mt-4 max-w-md text-base leading-7 text-primary-foreground/78">
              Autonomous CFO Operating System for verified financial decisions. Engines own every number; AI explains the decision trail.
            </p>
            <div className="mt-8 flex flex-wrap gap-2">
              <Badge variant="outline" className="border-primary-foreground/25 text-primary-foreground">
                Deterministic engines
              </Badge>
              <Badge variant="outline" className="border-primary-foreground/25 text-primary-foreground">
                Audit replay
              </Badge>
              <Badge variant="outline" className="border-primary-foreground/25 text-primary-foreground">
                Tool-routed CFO Chat
              </Badge>
            </div>
          </section>

          <section>
            <div className="mb-5">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Dev login</div>
              <h2 className="mt-2 font-display text-3xl font-semibold">Choose the operating profile</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                The selected user type is persisted in local session and drives organization-specific data, navigation, feed, chat, and simulations.
              </p>
            </div>
            {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
            <div className="grid gap-4 md:grid-cols-2">
              {demos.map((demo) => {
                const Icon = demo.userType === "startup" ? Building2 : BriefcaseBusiness;
                return (
                  <Card key={demo.userType} className="overflow-hidden">
                    <CardHeader className="border-b">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <CardTitle>{demo.title}</CardTitle>
                          <p className="mt-2 text-sm leading-6 text-muted-foreground">{demo.subtitle}</p>
                        </div>
                        <div className="rounded-lg border bg-background p-2">
                          <Icon className="size-5 text-primary" />
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4 pt-5">
                      {demo.bullets.map((bullet) => (
                        <div key={bullet} className="flex items-center gap-2 text-sm">
                          <ShieldCheck className="size-4 text-primary" />
                          {bullet}
                        </div>
                      ))}
                      <Button className="w-full" onClick={() => selectDemo(demo.userType)} disabled={loading !== null}>
                        {loading === demo.userType ? "Starting session..." : `Login as ${demo.title}`}
                      </Button>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

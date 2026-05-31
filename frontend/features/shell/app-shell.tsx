"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Activity, Bot, BriefcaseBusiness, ClipboardCheck, DollarSign, Gauge, Inbox, ListChecks, LogOut, Plug, ReceiptText, Scissors, Send, SplitSquareVertical, TrendingUp, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { currentOrgId, currentUserType, logout } from "@/services/api";
import type { UserType } from "@/types/api";

const startupNav = [
  { href: "/dashboard", label: "Command Center", icon: Gauge },
  { href: "/feed", label: "CFO Feed", icon: ListChecks },
  { href: "/simulate", label: "Simulate", icon: SplitSquareVertical },
  { href: "/hiring", label: "Hiring", icon: Users },
  { href: "/fundraising", label: "Fundraising", icon: TrendingUp },
  { href: "/vendors", label: "Vendors", icon: Scissors },
  { href: "/chat", label: "CFO Chat", icon: Bot },
  { href: "/audit", label: "Audit", icon: ClipboardCheck },
  { href: "/settings/integrations", label: "Integrations", icon: Plug }
];

const freelancerNav = [
  { href: "/dashboard", label: "Command Center", icon: Gauge },
  { href: "/receivables", label: "Receivables", icon: Inbox },
  { href: "/follow-ups", label: "Follow-ups", icon: Send },
  { href: "/cash-gap", label: "Cash Gap", icon: DollarSign },
  { href: "/tax-reserve", label: "Tax Reserve", icon: ReceiptText },
  { href: "/client-profitability", label: "Client Profitability", icon: BriefcaseBusiness },
  { href: "/chat", label: "CFO Chat", icon: Bot },
  { href: "/audit", label: "Audit", icon: ClipboardCheck },
  { href: "/settings/integrations", label: "Integrations", icon: Plug }
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [userType, setUserType] = useState<UserType>("startup");

  useEffect(() => {
    if (!currentOrgId()) {
      router.replace("/login");
      return;
    }
    setUserType(currentUserType() ?? "startup");
  }, [router]);

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  const nav = userType === "startup" ? startupNav : freelancerNav;

  return (
    <div className="min-h-screen finance-grid">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r bg-background/92 backdrop-blur-xl lg:block">
        <div className="flex h-full flex-col">
          <div className="border-b px-5 py-5">
            <div className="flex items-center gap-3">
              <BrandMark />
              <div>
                <div className="font-display text-xl font-semibold leading-none">clariFi</div>
                <div className="text-xs text-muted-foreground">CFO Operating System</div>
              </div>
            </div>
          </div>
          <nav className="flex-1 space-y-1 px-3 py-4">
            {nav.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition hover:bg-muted/70 hover:text-foreground",
                    active && "bg-card text-foreground shadow-sm"
                  )}
                >
                  <Icon className="size-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="border-t p-4">
            <div className="rounded-lg border bg-card p-3">
              <div className="flex items-center gap-2 text-xs font-semibold">
                <Activity className="size-3.5 text-primary" />
                {userType === "startup" ? "Founder mode" : "Freelancer mode"}
              </div>
              <p className="mt-2 text-xs leading-5 text-muted-foreground">
                Models explain verified facts. Engines own every number.
              </p>
              <div className="mt-3 flex items-center justify-between gap-2">
                <Badge variant="outline">Audit-ready</Badge>
                <Button size="sm" variant="ghost" onClick={handleLogout}>
                  <LogOut className="size-3" />
                  Logout
                </Button>
              </div>
            </div>
          </div>
        </div>
      </aside>
      <main className="lg:pl-64">
        <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
          <div className="mb-5 flex items-center justify-between rounded-lg border bg-background/80 px-4 py-3 shadow-sm backdrop-blur lg:hidden">
            <div className="flex items-center gap-2">
              <BrandMark compact />
              <div className="font-display text-xl font-semibold">clariFi</div>
            </div>
            <Link className="text-sm font-semibold text-primary" href="/login">Switch</Link>
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}

function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className={cn("relative flex items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm", compact ? "size-8" : "size-9")}>
      <div className="absolute left-2 top-2 size-2 rounded-full bg-primary-foreground/85" />
      <div className="absolute bottom-2 right-2 size-3 rounded-sm border border-primary-foreground/80" />
      <span className="font-display text-sm font-semibold">cf</span>
    </div>
  );
}

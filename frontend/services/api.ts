"use client";

import type {
  AuditLog,
  ChatResponse,
  Connector,
  DashboardSummary,
  DevLoginResponse,
  Feed,
  FinancialFact,
  Organization,
  Action,
  ReceivableInvoice,
  Recommendation,
  UserType,
  WorkflowRun
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const ORG_KEY = "clarifi_org_id";
const USER_TYPE_KEY = "clarifi_user_type";

export async function ensureSession(userType?: UserType): Promise<DevLoginResponse> {
  if (typeof window === "undefined") {
    throw new Error("ensureSession must run in the browser");
  }
  const existing = window.localStorage.getItem(ORG_KEY);
  const requested = userType ?? (window.localStorage.getItem(USER_TYPE_KEY) as UserType | null) ?? "startup";
  if (existing && !userType) {
    return {
      user_id: "local",
      organization_id: existing,
      user_type: requested,
      email: `${requested}@clarifi.local`
    };
  }
  const session = await apiFetch<DevLoginResponse>("/auth/dev-login", {
    method: "POST",
    body: JSON.stringify({ user_type: requested }),
    skipOrg: true
  });
  window.localStorage.setItem(ORG_KEY, session.organization_id);
  window.localStorage.setItem(USER_TYPE_KEY, session.user_type);
  return session;
}

export async function loginAs(userType: UserType): Promise<DevLoginResponse> {
  return ensureSession(userType);
}

export function logout() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ORG_KEY);
  window.localStorage.removeItem(USER_TYPE_KEY);
}

export function currentOrgId() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ORG_KEY);
}

export function currentUserType(): UserType | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(USER_TYPE_KEY) as UserType | null;
}

export async function apiFetch<T>(path: string, init: RequestInit & { skipOrg?: boolean } = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("content-type", "application/json");
  if (!init.skipOrg && typeof window !== "undefined") {
    const orgId = window.localStorage.getItem(ORG_KEY);
    if (orgId) headers.set("x-org-id", orgId);
  }
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store"
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  currentOrganization: () => apiFetch<Organization>("/organizations/current"),
  connectors: () => apiFetch<Connector[]>("/connectors"),
  connect: (type: string) => apiFetch<Connector>(`/connectors/${type}/connect`, { method: "POST" }),
  sync: (id: string) => apiFetch<{ connector_id: string; stats: Record<string, number> }>(`/connectors/${id}/sync`, { method: "POST" }),
  dashboard: () => apiFetch<DashboardSummary>("/dashboard/summary"),
  facts: () => apiFetch<FinancialFact[]>("/facts"),
  recommendations: () => apiFetch<Recommendation[]>("/recommendations"),
  approveRecommendation: (id: string) => apiFetch<Recommendation>(`/recommendations/${id}/approve`, { method: "POST" }),
  dismissRecommendation: (id: string) => apiFetch<Recommendation>(`/recommendations/${id}/dismiss`, { method: "POST" }),
  feed: () => apiFetch<Feed>("/feed"),
  receivables: () => apiFetch<ReceivableInvoice[]>("/receivables"),
  createFollowUpDraft: (payload: { invoice_id: string; tone?: string; to?: string; subject?: string; body?: string }) =>
    apiFetch<Action>("/actions/follow-up-draft", { method: "POST", body: JSON.stringify(payload) }),
  markActionSent: (id: string) => apiFetch<Action>(`/actions/${id}/mark-sent`, { method: "POST" }),
  simulateHiring: (payload: {
    monthly_cost: number;
    role?: string;
    benefits_multiplier?: number;
    equipment_cost?: number;
    software_seat_cost?: number;
    recruiting_onboarding_cost?: number;
    start_date?: string;
  }) =>
    apiFetch<Record<string, unknown>>("/simulate/hiring", { method: "POST", body: JSON.stringify(payload) }),
  simulateVendorCut: (payload: { vendor_name: string; monthly_savings: number; cancellation_date?: string; operational_risk_note?: string }) =>
    apiFetch<Record<string, unknown>>("/simulate/vendor-cut", { method: "POST", body: JSON.stringify(payload) }),
  simulateInvoiceCollection: (payload: { invoice_id?: string; expected_payment_date?: string; probability?: number }) =>
    apiFetch<Record<string, unknown>>("/simulate/invoice-collection", { method: "POST", body: JSON.stringify(payload) }),
  chat: (question: string, thread_id?: string) =>
    apiFetch<ChatResponse>("/chat", { method: "POST", body: JSON.stringify({ question, thread_id }) }),
  audit: () => apiFetch<AuditLog[]>("/audit"),
  workflowRuns: () => apiFetch<WorkflowRun[]>("/workflow-runs"),
  searchDocuments: (query: string) => apiFetch<{ items: unknown[] }>(`/documents/search?q=${encodeURIComponent(query)}`),
  runFinancialAnalysis: () => apiFetch<{ workflow_run_id: string; memo_id: string }>("/workflows/financial-analysis", { method: "POST" }),
  runReceivables: () => apiFetch<{ workflow_run_id: string; action_ids: string[] }>("/workflows/receivables", { method: "POST" }),
  runFundraising: () => apiFetch<Record<string, unknown>>("/workflows/fundraising", { method: "POST" })
};

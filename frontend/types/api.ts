export type UserType = "startup" | "freelancer";

export type DevLoginResponse = {
  user_id: string;
  organization_id: string;
  user_type: UserType;
  email: string;
};

export type Organization = {
  id: string;
  name: string;
  user_type: UserType;
  currency: string;
  settings: Record<string, unknown>;
};

export type DashboardSummary = {
  organization: Organization;
  metrics: {
    current_cash: number;
    monthly_burn: number;
    runway_months: number;
    receivables: number;
    overdue_receivables: number;
    payables_30d: number;
    risk_score: number;
  };
  top_risks: { title: string; message: string; severity: string }[];
  recommended_actions: { id: string; title: string; impact: string; recommended_action: string; confidence_score: number }[];
  facts: FinancialFact[];
};

export type FinancialFact = {
  id: string;
  fact_type: string;
  value: number;
  currency: string;
  formula: string;
  engine_name: string;
  engine_version: string;
  source_record_ids: string[];
  audit_log_id: string;
  created_at: string;
};

export type Recommendation = {
  id: string;
  organization_id: string;
  user_type?: UserType | null;
  stable_key?: string | null;
  title: string;
  description?: string | null;
  issue: string;
  impact: string;
  recommended_action: string;
  confidence_score: number;
  confidence?: number;
  status: string;
  evidence: EvidenceItem[];
  financial_impact_amount?: number | null;
  impact_amount?: number | null;
  impact_metric?: string | null;
  primary_cta?: string | null;
  secondary_cta?: string | null;
  source_fact_ids: string[];
  audit_log_id?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type Alert = {
  id: string;
  severity: string;
  title: string;
  message: string;
  status: string;
  evidence: EvidenceItem[];
};

export type EvidenceItem = {
  source_type: string;
  source_id: string;
  title: string;
  excerpt: string;
  amount?: string | number | null;
  metadata?: Record<string, unknown>;
};

export type Connector = {
  id?: string | null;
  type: string;
  display_name?: string;
  status: string;
  mode?: string;
  available?: boolean;
  implemented?: boolean;
  description?: string;
  last_synced_at?: string | null;
};

export type Action = {
  id: string;
  action_type: string;
  status: string;
  title: string;
  payload: Record<string, unknown>;
  approval_required: boolean;
};

export type Feed = {
  recommendations: Recommendation[];
  alerts: Alert[];
  actions: Action[];
  memos: { id: string; title: string; summary: string; risks: unknown[]; actions: unknown[] }[];
};

export type ReceivableInvoice = {
  id: string;
  invoice_number: string;
  customer_name: string;
  customer_email?: string | null;
  amount: number;
  paid_amount: number;
  due_on: string;
  issued_on: string;
  status: string;
  days_overdue: number;
  priority: string;
  suggested_action: string;
};

export type ChatResponse = {
  answer: string;
  thread_id: string;
  tools_used: string[];
  evidence: EvidenceItem[];
  audit_log_id: string;
  verification: {
    passed: boolean;
    reason: string;
    unsupported_numbers: string[];
    unsupported_claims: string[];
  };
};

export type AuditLog = {
  id: string;
  event_type: string;
  entity_type: string;
  action: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  prompt_version?: string;
  model_used?: string;
  verification_status: string;
  duration_ms?: number;
  created_at: string;
};

export type WorkflowRun = {
  id: string;
  workflow_name: string;
  status: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  duration_ms?: number;
  created_at: string;
  steps: {
    id: string;
    step_name: string;
    status: string;
    inputs: Record<string, unknown>;
    outputs: Record<string, unknown>;
    duration_ms?: number;
  }[];
};

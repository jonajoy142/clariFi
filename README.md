# clariFi CFO OS

Autonomous CFO Operating System for two users:

- Startup founders
- Freelancers and agencies

clariFi continuously normalizes financial data, creates a financial truth layer, runs deterministic Python engines, stores calculation receipts as `financial_facts`, retrieves evidence from documents, and generates CFO recommendations and chat answers from verified facts only.

Core rule: **LLMs never calculate financial numbers.** They can explain, summarize, plan tool calls, and draft memos from a `FinancialContextPack`, but every financial number must come from deterministic engines and be audit logged.

## Architecture

```text
Data sources
  -> Connector adapters
  -> Normalization layer
  -> PostgreSQL financial truth layer
  -> Deterministic engines
  -> FinancialFact + AuditLog
  -> LangGraph-ready workflows
  -> RAG evidence retrieval
  -> Verification layer
  -> CFO Feed + CFO Chat + Simulation UI
```

Backend structure:

```text
backend/app/
  api/              thin FastAPI routes
  db/               SQLAlchemy session/base
  models/           financial truth schema
  repositories/     database access
  services/         business orchestration
  engines/          deterministic financial math
  connectors/       mock adapters with real interface boundaries
  ai/
    tools/          MCP-compatible tool registry
    workflows/      LangGraph-ready workflow classes
    schemas/        Pydantic AI output schemas
    verification/   numeric grounding checks
    rag/            pgvector-ready evidence retrieval
  workers/          Celery worker and tasks
```

Frontend structure:

```text
frontend/
  app/              Next.js App Router routes
  features/         domain-specific UI modules
  components/ui/    shadcn-style primitives
  services/         typed API client
  types/            shared response types
```

## MVP Features

- Dev onboarding for startup founder or freelancer/agency
- Mock Zoho Books, Stripe, Razorpay, Gmail, Google Drive, and CSV connectors
- PostgreSQL schema for organizations, connectors, sync jobs, transactions, invoices, subscriptions, documents, facts, recommendations, audit logs, workflows, and evals
- Deterministic engines for cash, burn, runway, receivables, payables, vendor waste, hiring scenario, tax reserve, and forecast
- CFO Command Center with current cash, burn, runway, receivables, payables, risk score, and recommendations
- CFO Feed with operational cards: issue, impact, evidence, recommended action, approve/dismiss
- Runway Simulator for hiring and vendor cuts
- Receivables workflow with draft follow-up actions
- CFO Chat that plans tools, runs deterministic calculations, builds a `FinancialContextPack`, retrieves evidence, verifies numeric grounding, and audit logs the answer
- Workflow replay through `workflow_runs` and `workflow_steps`
- Docker Compose for Postgres + pgvector, Redis, backend, worker, and frontend

## Demo Data

Startup founder:

- Cash: `₹23,00,000`
- Monthly burn: `₹2,10,000`
- Runway: about `10.95` months
- Overdue invoice: `₹1,80,000`
- AWS spend spike: `₹50,000 -> ₹69,000`, `+38%`
- Payroll, SaaS subscriptions, Stripe revenue, Razorpay revenue

Freelancer/agency:

- Cash: `₹2,40,000`
- Overdue invoice: `₹42,000`, `18` days overdue
- Repeated late-paying client context
- Recent income for tax reserve estimate
- SaaS subscriptions and project expenses

## Run Locally

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

Manual backend setup:

```bash
cd backend
cp .env.example .env
poetry install
poetry run alembic upgrade head
poetry run uvicorn main:app --reload
```

Manual frontend setup:

```bash
cd frontend
npm install
npm run dev
```

## Demo Login

Use `/onboarding` in the frontend, or call:

```bash
curl -X POST http://localhost:8000/auth/dev-login \
  -H "content-type: application/json" \
  -d '{"user_type":"startup"}'
```

Use `user_type: "freelancer"` for the freelancer/agency demo.

## Tests

Backend tests cover deterministic engines, numeric grounding, workflow execution, and core API flows.

```bash
cd backend
poetry run pytest
```

## Current Limitations

- External connectors are mock adapters with production-shaped interfaces.
- Email follow-up actions are drafts only; no email is sent.
- RAG uses a deterministic local embedding abstraction and lexical retrieval for local portability; the schema is pgvector-ready.
- LangGraph is represented through independently testable workflow classes with optional import readiness; real graph compilation can be expanded once model/provider credentials are configured.
- LiteLLM/Langfuse/OpenTelemetry are wired architecturally, but model calls default to deterministic templates so the demo works without API keys.

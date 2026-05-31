from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.ai.workflows.cfo_chat_workflow import CFOChatWorkflow
from app.ai.workflows.financial_analysis_workflow import FinancialAnalysisWorkflow
from app.ai.workflows.fundraising_timing_workflow import FundraisingTimingWorkflow
from app.ai.workflows.receivables_workflow import ReceivablesWorkflow
from app.api.dependencies import CurrentOrgId, DbSession
from app.models.finance import Action, Alert, AuditLog, CFOMemo, Customer, FinancialFact, Invoice, Recommendation, WorkflowRun, WorkflowStep
from app.repositories.finance import (
    AuditRepository,
    FinanceRepository,
    OrganizationRepository,
    RecommendationRepository,
    WorkflowRepository,
)
from app.schemas.api import (
    ChatRequest,
    DevLoginRequest,
    DevLoginResponse,
    DocumentSearchResponse,
    DocumentUploadRequest,
    HiringSimulationRequest,
    VendorCutSimulationRequest,
)
from app.services.connectors import ConnectorService
from app.services.dashboard import DashboardService
from app.services.documents import DocumentService
from app.services.facts import FinancialFactService
from app.services.recommendations import RecommendationService
from app.services.seed import seed_user_type
from app.services.simulation import SimulationService

router = APIRouter()


@router.post("/auth/dev-login", response_model=DevLoginResponse)
def dev_login(payload: DevLoginRequest, db: DbSession):
    org = seed_user_type(db, payload.user_type)
    db.commit()
    user = org.members[0].user if org.members else None
    return DevLoginResponse(
        user_id=user.id if user else "dev",
        organization_id=org.id,
        user_type=org.user_type,
        email=user.email if user else f"{payload.user_type}@clarifi.local",
    )


@router.get("/organizations/current")
def current_organization(db: DbSession, organization_id: CurrentOrgId):
    org = OrganizationRepository(db).get(organization_id)
    return {
        "id": org.id,
        "name": org.name,
        "user_type": org.user_type,
        "currency": org.currency,
        "settings": org.settings or {},
    }


@router.get("/connectors")
def list_connectors(db: DbSession, organization_id: CurrentOrgId):
    return ConnectorService(db).catalog(organization_id)


@router.post("/connectors/{connector_type}/connect")
def connect_connector(connector_type: str, db: DbSession, organization_id: CurrentOrgId):
    try:
        connector = ConnectorService(db).connect(organization_id, connector_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": connector.id, "type": connector.type, "status": connector.status, "display_name": connector.config.get("display_name"), "mode": connector.config.get("mode", "mock")}


@router.post("/connectors/{connector_id}/sync")
def sync_connector(connector_id: str, db: DbSession, organization_id: CurrentOrgId):
    try:
        return ConnectorService(db).sync(organization_id, connector_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/dashboard/summary")
def dashboard_summary(db: DbSession, organization_id: CurrentOrgId):
    return DashboardService(db).summary(organization_id)


@router.get("/facts")
def facts(db: DbSession, organization_id: CurrentOrgId):
    if not FinanceRepository(db).facts(organization_id):
        FinancialFactService(db).calculate_and_persist(organization_id)
        db.commit()
    return [_serialize_fact(fact) for fact in FinanceRepository(db).facts(organization_id)]


@router.get("/recommendations")
def recommendations(db: DbSession, organization_id: CurrentOrgId, status: str | None = None):
    if not RecommendationRepository(db).list(organization_id):
        RecommendationService(db).regenerate(organization_id)
        db.commit()
    return [_serialize_recommendation(rec) for rec in RecommendationRepository(db).list(organization_id, status=status)]


@router.post("/recommendations/{recommendation_id}/approve")
def approve_recommendation(recommendation_id: str, db: DbSession, organization_id: CurrentOrgId):
    rec = RecommendationRepository(db).set_status(organization_id, recommendation_id, "approved")
    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    AuditRepository(db).create(
        organization_id=organization_id,
        event_type="action",
        actor_type="user",
        entity_type="recommendation",
        entity_id=rec.id,
        action="recommendation.approve",
        inputs={},
        outputs={"status": rec.status},
        verification_status="approved_by_user",
    )
    db.commit()
    return _serialize_recommendation(rec)


@router.post("/recommendations/{recommendation_id}/dismiss")
def dismiss_recommendation(recommendation_id: str, db: DbSession, organization_id: CurrentOrgId):
    rec = RecommendationRepository(db).set_status(organization_id, recommendation_id, "dismissed")
    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    AuditRepository(db).create(
        organization_id=organization_id,
        event_type="action",
        actor_type="user",
        entity_type="recommendation",
        entity_id=rec.id,
        action="recommendation.dismiss",
        inputs={},
        outputs={"status": rec.status},
        verification_status="dismissed_by_user",
    )
    db.commit()
    return _serialize_recommendation(rec)


@router.get("/alerts")
def alerts(db: DbSession, organization_id: CurrentOrgId):
    return [_serialize_alert(alert) for alert in RecommendationRepository(db).alerts(organization_id)]


@router.get("/feed")
def feed(db: DbSession, organization_id: CurrentOrgId):
    _ensure_facts(db, organization_id)
    RecommendationService(db).regenerate(organization_id)
    db.commit()
    alerts_list = RecommendationRepository(db).alerts(organization_id)
    recs = RecommendationRepository(db).list(organization_id)
    actions = db.scalars(select(Action).where(Action.organization_id == organization_id).order_by(Action.created_at.desc())).all()
    memos = db.scalars(select(CFOMemo).where(CFOMemo.organization_id == organization_id).order_by(CFOMemo.created_at.desc())).all()
    return {
        "recommendations": [_serialize_recommendation(rec) for rec in recs],
        "alerts": [_serialize_alert(alert) for alert in alerts_list],
        "actions": [
            {
                "id": action.id,
                "action_type": action.action_type,
                "status": action.status,
                "title": action.title,
                "payload": action.payload,
                "approval_required": action.approval_required,
            }
            for action in actions
        ],
        "memos": [
            {"id": memo.id, "title": memo.title, "summary": memo.summary, "risks": memo.risks, "actions": memo.actions}
            for memo in memos
        ],
    }


@router.post("/simulate/hiring")
def simulate_hiring(payload: HiringSimulationRequest, db: DbSession, organization_id: CurrentOrgId):
    _ensure_facts(db, organization_id)
    return _serialize_decimal_dict(
        SimulationService(db).hiring(
            organization_id,
            payload.monthly_cost,
            payload.role,
            benefits_multiplier=payload.benefits_multiplier,
            equipment_cost=payload.equipment_cost,
            software_seat_cost=payload.software_seat_cost,
            recruiting_onboarding_cost=payload.recruiting_onboarding_cost,
            start_date=payload.start_date,
        )
    )


@router.post("/simulate/vendor-cut")
def simulate_vendor_cut(payload: VendorCutSimulationRequest, db: DbSession, organization_id: CurrentOrgId):
    _ensure_facts(db, organization_id)
    return _serialize_decimal_dict(SimulationService(db).vendor_cut(organization_id, payload.monthly_savings, payload.vendor_name, payload.cancellation_date, payload.operational_risk_note))


@router.post("/simulate/invoice-collection")
def simulate_invoice_collection(payload: dict, db: DbSession, organization_id: CurrentOrgId):
    _ensure_facts(db, organization_id)
    return _serialize_decimal_dict(
        SimulationService(db).invoice_collection(
            organization_id,
            invoice_id=payload.get("invoice_id"),
            expected_payment_date=payload.get("expected_payment_date"),
            probability=Decimal(str(payload.get("probability", "0.75"))),
        )
    )


@router.get("/receivables")
def receivables(db: DbSession, organization_id: CurrentOrgId):
    invoices = db.scalars(select(Invoice).where(Invoice.organization_id == organization_id, Invoice.direction == "receivable").order_by(Invoice.due_on)).all()
    customers = {customer.id: customer for customer in db.scalars(select(Customer).where(Customer.organization_id == organization_id)).all()}
    return [
        {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "customer_name": customers.get(invoice.customer_id).name if invoice.customer_id and customers.get(invoice.customer_id) else "Unknown client",
            "customer_email": customers.get(invoice.customer_id).email if invoice.customer_id and customers.get(invoice.customer_id) else None,
            "amount": float(invoice.amount),
            "paid_amount": float(invoice.paid_amount),
            "due_on": invoice.due_on,
            "issued_on": invoice.issued_on,
            "status": invoice.status,
            "days_overdue": max(0, (date.today() - invoice.due_on).days),
            "priority": "high" if invoice.status == "overdue" or (date.today() - invoice.due_on).days >= 14 else "normal",
            "suggested_action": "Send firm follow-up" if invoice.status == "overdue" else "Monitor",
        }
        for invoice in invoices
    ]


@router.post("/actions/follow-up-draft")
def create_follow_up_draft(payload: dict, db: DbSession, organization_id: CurrentOrgId):
    invoice = db.get(Invoice, payload.get("invoice_id"))
    if invoice is None or invoice.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Invoice not found")
    customer = db.get(Customer, invoice.customer_id) if invoice.customer_id else None
    tone = payload.get("tone", "polite")
    subject = payload.get("subject") or f"Follow-up on invoice {invoice.invoice_number}"
    body = payload.get("body") or _follow_up_body(customer.name if customer else "there", invoice.invoice_number, Decimal(str(invoice.amount)), invoice.due_on.isoformat(), tone)
    action = Action(
        organization_id=organization_id,
        action_type="email_draft",
        status="draft",
        title=f"Follow up on {invoice.invoice_number}",
        payload={
            "to": payload.get("to") or (customer.email if customer else ""),
            "subject": subject,
            "body": body,
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "amount": str(invoice.amount),
            "due_on": invoice.due_on.isoformat(),
            "tone": tone,
        },
        approval_required=True,
    )
    db.add(action)
    db.flush()
    AuditRepository(db).create(
        organization_id=organization_id,
        event_type="action",
        actor_type="user",
        entity_type="action",
        action="follow_up_draft.save",
        inputs=payload,
        outputs={"action_id": action.id, "invoice_id": invoice.id},
        verification_status="draft_saved",
    )
    db.commit()
    db.refresh(action)
    return _serialize_action(action)


@router.post("/actions/{action_id}/mark-sent")
def mark_action_sent(action_id: str, db: DbSession, organization_id: CurrentOrgId):
    action = db.get(Action, action_id)
    if action is None or action.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Action not found")
    action.status = "sent"
    db.commit()
    return _serialize_action(action)


@router.post("/chat")
def chat(payload: ChatRequest, db: DbSession, organization_id: CurrentOrgId):
    _ensure_facts(db, organization_id)
    return CFOChatWorkflow(db).run(organization_id, payload.question, payload.thread_id)


@router.get("/audit")
def audit(db: DbSession, organization_id: CurrentOrgId):
    return [
        {
            "id": log.id,
            "event_type": log.event_type,
            "entity_type": log.entity_type,
            "action": log.action,
            "inputs": log.inputs,
            "outputs": log.outputs,
            "prompt_version": log.prompt_version,
            "model_used": log.model_used,
            "verification_status": log.verification_status,
            "duration_ms": log.duration_ms,
            "created_at": log.created_at,
        }
        for log in AuditRepository(db).list(organization_id)
    ]


@router.get("/workflow-runs")
def workflow_runs(db: DbSession, organization_id: CurrentOrgId):
    runs = WorkflowRepository(db).list(organization_id)
    steps = db.scalars(select(WorkflowStep).where(WorkflowStep.workflow_run_id.in_([run.id for run in runs]))).all() if runs else []
    by_run: dict[str, list] = {}
    for step in steps:
        by_run.setdefault(step.workflow_run_id, []).append(step)
    return [
        {
            "id": run.id,
            "workflow_name": run.workflow_name,
            "status": run.status,
            "inputs": run.inputs,
            "outputs": run.outputs,
            "error": run.error,
            "duration_ms": run.duration_ms,
            "created_at": run.created_at,
            "steps": [
                {
                    "id": step.id,
                    "step_name": step.step_name,
                    "status": step.status,
                    "inputs": step.inputs,
                    "outputs": step.outputs,
                    "duration_ms": step.duration_ms,
                }
                for step in by_run.get(run.id, [])
            ],
        }
        for run in runs
    ]


@router.post("/documents/upload")
def upload_document(payload: DocumentUploadRequest, db: DbSession, organization_id: CurrentOrgId):
    document = DocumentService(db).ingest(organization_id, title=payload.title, text=payload.text, document_type=payload.document_type, source=payload.source)
    db.commit()
    return {"id": document.id, "title": document.title, "status": document.status}


@router.get("/documents/search", response_model=DocumentSearchResponse)
def search_documents(db: DbSession, organization_id: CurrentOrgId, q: str = Query(..., min_length=2)):
    return {"items": DocumentService(db).search(organization_id, q)}


@router.post("/workflows/financial-analysis")
def run_financial_analysis(db: DbSession, organization_id: CurrentOrgId):
    return FinancialAnalysisWorkflow(db).run(organization_id)


@router.post("/workflows/receivables")
def run_receivables(db: DbSession, organization_id: CurrentOrgId):
    return ReceivablesWorkflow(db).run(organization_id)


@router.post("/workflows/fundraising")
def run_fundraising(db: DbSession, organization_id: CurrentOrgId):
    _ensure_facts(db, organization_id)
    return FundraisingTimingWorkflow(db).run(organization_id)


def _ensure_facts(db, organization_id: str) -> None:
    if not FinanceRepository(db).facts(organization_id):
        FinancialFactService(db).calculate_and_persist(organization_id)
        RecommendationService(db).regenerate(organization_id)
        db.commit()


def _serialize_fact(fact: FinancialFact) -> dict:
    return {
        "id": fact.id,
        "fact_type": fact.fact_type,
        "value": float(fact.value),
        "currency": fact.currency,
        "period_start": fact.period_start,
        "period_end": fact.period_end,
        "formula": fact.formula,
        "source_record_ids": fact.source_record_ids,
        "engine_name": fact.engine_name,
        "engine_version": fact.engine_version,
        "confidence_score": float(fact.confidence_score),
        "audit_log_id": fact.audit_log_id,
        "created_at": fact.created_at,
    }


def _serialize_recommendation(rec: Recommendation) -> dict:
    return {
        "id": rec.id,
        "organization_id": rec.organization_id,
        "user_type": rec.user_type,
        "stable_key": rec.stable_key,
        "title": rec.title,
        "description": rec.description,
        "issue": rec.issue,
        "impact": rec.impact,
        "recommended_action": rec.recommended_action,
        "confidence_score": float(rec.confidence_score),
        "confidence": float(rec.confidence_score),
        "status": rec.status,
        "evidence": rec.evidence,
        "financial_impact_amount": float(rec.financial_impact_amount) if rec.financial_impact_amount is not None else None,
        "impact_amount": float(rec.financial_impact_amount) if rec.financial_impact_amount is not None else None,
        "impact_metric": rec.impact_metric,
        "primary_cta": rec.primary_cta,
        "secondary_cta": rec.secondary_cta,
        "source_fact_ids": rec.source_fact_ids,
        "audit_log_id": rec.audit_log_id,
        "created_at": rec.created_at,
        "updated_at": rec.updated_at,
    }


def _serialize_alert(alert: Alert) -> dict:
    return {
        "id": alert.id,
        "severity": alert.severity,
        "title": alert.title,
        "message": alert.message,
        "status": alert.status,
        "evidence": alert.evidence,
    }


def _serialize_decimal_dict(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _serialize_decimal_dict(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_decimal_dict(item) for item in value]
    return value


def _serialize_action(action: Action) -> dict:
    return {
        "id": action.id,
        "action_type": action.action_type,
        "status": action.status,
        "title": action.title,
        "payload": action.payload,
        "approval_required": action.approval_required,
    }


def _follow_up_body(customer_name: str, invoice_number: str, amount: Decimal, due_on: str, tone: str) -> str:
    opener = {
        "polite": "I hope you are doing well. I wanted to gently follow up",
        "firm": "I am following up again",
        "final_notice": "This is a final reminder before we escalate internally",
    }.get(tone, "I wanted to follow up")
    return (
        f"Hi {customer_name},\n\n"
        f"{opener} on invoice {invoice_number} for ₹{amount:,.0f}, due on {due_on}. "
        "Could you confirm the payment date?\n\n"
        "Regards"
    )

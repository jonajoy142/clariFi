from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.finance import (
    Action,
    Alert,
    AuditLog,
    BankAccount,
    CFOMemo,
    ChatMessage,
    ChatThread,
    Connector,
    Customer,
    Document,
    DocumentChunk,
    FinancialFact,
    Invoice,
    Organization,
    Recommendation,
    Subscription,
    SyncJob,
    Transaction,
    User,
    Vendor,
    WorkflowRun,
    WorkflowStep,
)


class OrganizationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, organization_id: str) -> Organization | None:
        return self.db.get(Organization, organization_id)

    def by_user_type(self, user_type: str) -> Organization | None:
        return self.db.scalar(select(Organization).where(Organization.user_type == user_type).order_by(Organization.created_at))

    def create_with_owner(self, *, user_type: str, name: str, email: str) -> tuple[User, Organization]:
        user = self.db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, name=name)
            self.db.add(user)
            self.db.flush()
        org = self.db.scalar(select(Organization).where(Organization.name == name, Organization.user_type == user_type))
        if org is None:
            from app.models.finance import OrganizationMember

            org = Organization(name=name, user_type=user_type, currency="INR")
            self.db.add(org)
            self.db.flush()
            self.db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="owner"))
            self.db.flush()
        return user, org


class ConnectorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, connector_id: str) -> Connector | None:
        return self.db.get(Connector, connector_id)

    def list_for_org(self, organization_id: str) -> Sequence[Connector]:
        return self.db.scalars(select(Connector).where(Connector.organization_id == organization_id).order_by(Connector.type)).all()

    def get_or_create(self, organization_id: str, connector_type: str) -> Connector:
        connector = self.db.scalar(
            select(Connector).where(Connector.organization_id == organization_id, Connector.type == connector_type)
        )
        if connector is None:
            connector = Connector(organization_id=organization_id, type=connector_type, status="disconnected")
            self.db.add(connector)
            self.db.flush()
        return connector

    def create_sync_job(self, organization_id: str, connector_id: str | None, status: str = "queued", stats: dict[str, Any] | None = None) -> SyncJob:
        job = SyncJob(organization_id=organization_id, connector_id=connector_id, status=status, stats=stats or {})
        self.db.add(job)
        self.db.flush()
        return job


class FinanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def accounts(self, organization_id: str) -> Sequence[BankAccount]:
        return self.db.scalars(select(BankAccount).where(BankAccount.organization_id == organization_id)).all()

    def transactions(self, organization_id: str) -> Sequence[Transaction]:
        return self.db.scalars(select(Transaction).where(Transaction.organization_id == organization_id)).all()

    def invoices(self, organization_id: str) -> Sequence[Invoice]:
        return self.db.scalars(select(Invoice).where(Invoice.organization_id == organization_id)).all()

    def vendors(self, organization_id: str) -> Sequence[Vendor]:
        return self.db.scalars(select(Vendor).where(Vendor.organization_id == organization_id)).all()

    def subscriptions(self, organization_id: str) -> Sequence[Subscription]:
        return self.db.scalars(select(Subscription).where(Subscription.organization_id == organization_id)).all()

    def payroll(self, organization_id: str):
        from app.models.finance import PayrollItem

        return self.db.scalars(select(PayrollItem).where(PayrollItem.organization_id == organization_id)).all()

    def customers(self, organization_id: str) -> Sequence[Customer]:
        return self.db.scalars(select(Customer).where(Customer.organization_id == organization_id)).all()

    def replace_facts(self, organization_id: str, facts: list[FinancialFact]) -> None:
        self.db.execute(delete(FinancialFact).where(FinancialFact.organization_id == organization_id))
        self.db.add_all(facts)
        self.db.flush()

    def facts(self, organization_id: str) -> Sequence[FinancialFact]:
        return self.db.scalars(
            select(FinancialFact).where(FinancialFact.organization_id == organization_id).order_by(FinancialFact.fact_type)
        ).all()

    def latest_fact_map(self, organization_id: str) -> dict[str, FinancialFact]:
        facts = self.facts(organization_id)
        return {fact.fact_type: fact for fact in facts}


class RecommendationRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, organization_id: str, status: str | None = None) -> Sequence[Recommendation]:
        stmt = select(Recommendation).where(Recommendation.organization_id == organization_id)
        if status is not None:
            stmt = stmt.where(Recommendation.status == status)
        return self.db.scalars(stmt.order_by(Recommendation.updated_at.desc(), Recommendation.created_at.desc())).all()

    def upsert_generated(self, organization_id: str, recommendations: list[Recommendation], alerts: list[Alert]) -> None:
        existing_by_key = {
            rec.stable_key: rec
            for rec in self.db.scalars(
                select(Recommendation).where(
                    Recommendation.organization_id == organization_id,
                    Recommendation.stable_key.is_not(None),
                )
            ).all()
        }
        generated_keys = {rec.stable_key for rec in recommendations if rec.stable_key}
        for incoming in recommendations:
            existing = existing_by_key.get(incoming.stable_key) if incoming.stable_key else None
            if existing is None:
                incoming.status = "active"
                self.db.add(incoming)
                continue
            if existing.status in {"approved", "dismissed", "completed"}:
                continue
            existing.user_type = incoming.user_type
            existing.title = incoming.title
            existing.description = incoming.description
            existing.issue = incoming.issue
            existing.impact = incoming.impact
            existing.recommended_action = incoming.recommended_action
            existing.confidence_score = incoming.confidence_score
            existing.evidence = incoming.evidence
            existing.financial_impact_amount = incoming.financial_impact_amount
            existing.impact_metric = incoming.impact_metric
            existing.primary_cta = incoming.primary_cta
            existing.secondary_cta = incoming.secondary_cta
            existing.source_fact_ids = incoming.source_fact_ids
            existing.audit_log_id = incoming.audit_log_id
            existing.status = "active"

        stale_active = self.db.scalars(
            select(Recommendation).where(
                Recommendation.organization_id == organization_id,
                Recommendation.status == "active",
                Recommendation.stable_key.is_not(None),
            )
        ).all()
        for rec in stale_active:
            if rec.stable_key not in generated_keys:
                rec.status = "dismissed"

        self.db.execute(delete(Alert).where(Alert.organization_id == organization_id, Alert.status == "open"))
        self.db.add_all(alerts)
        self.db.flush()

    def set_status(self, organization_id: str, recommendation_id: str, status: str) -> Recommendation | None:
        rec = self.db.get(Recommendation, recommendation_id)
        if rec and rec.organization_id == organization_id:
            rec.status = status
            self.db.flush()
            return rec
        return None

    def alerts(self, organization_id: str) -> Sequence[Alert]:
        return self.db.scalars(select(Alert).where(Alert.organization_id == organization_id).order_by(Alert.created_at.desc())).all()


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs: Any) -> AuditLog:
        for key in ("inputs", "outputs"):
            if key in kwargs:
                kwargs[key] = _json_safe(kwargs[key])
        log = AuditLog(**kwargs)
        self.db.add(log)
        self.db.flush()
        return log

    def list(self, organization_id: str) -> Sequence[AuditLog]:
        return self.db.scalars(select(AuditLog).where(AuditLog.organization_id == organization_id).order_by(AuditLog.created_at.desc())).all()


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_document(self, document: Document, chunks: list[DocumentChunk]) -> Document:
        self.db.add(document)
        self.db.flush()
        for chunk in chunks:
            chunk.document_id = document.id
            self.db.add(chunk)
        self.db.flush()
        return document

    def chunks(self, organization_id: str) -> Sequence[DocumentChunk]:
        return self.db.scalars(select(DocumentChunk).where(DocumentChunk.organization_id == organization_id)).all()


class WorkflowRepository:
    def __init__(self, db: Session):
        self.db = db

    def start(self, organization_id: str, workflow_name: str, inputs: dict[str, Any]) -> WorkflowRun:
        run = WorkflowRun(organization_id=organization_id, workflow_name=workflow_name, status="running", inputs=_json_safe(inputs))
        self.db.add(run)
        self.db.flush()
        return run

    def step(self, run_id: str, step_name: str, inputs: dict[str, Any], outputs: dict[str, Any], status: str = "completed", error: str | None = None, duration_ms: int | None = None) -> WorkflowStep:
        step = WorkflowStep(
            workflow_run_id=run_id,
            step_name=step_name,
            inputs=_json_safe(inputs),
            outputs=_json_safe(outputs),
            status=status,
            error=error,
            duration_ms=duration_ms,
        )
        self.db.add(step)
        self.db.flush()
        return step

    def finish(self, run: WorkflowRun, outputs: dict[str, Any], status: str = "completed", error: str | None = None, duration_ms: int | None = None) -> WorkflowRun:
        run.outputs = _json_safe(outputs)
        run.status = status
        run.error = error
        run.duration_ms = duration_ms
        run.updated_at = datetime.utcnow()
        self.db.flush()
        return run

    def list(self, organization_id: str) -> Sequence[WorkflowRun]:
        return self.db.scalars(select(WorkflowRun).where(WorkflowRun.organization_id == organization_id).order_by(WorkflowRun.created_at.desc())).all()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value

import time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.finance import Alert, Recommendation
from app.repositories.finance import FinanceRepository, OrganizationRepository, WorkflowRepository


class FundraisingTimingWorkflow:
    def __init__(self, db: Session):
        self.db = db
        self.finance_repo = FinanceRepository(db)
        self.workflow_repo = WorkflowRepository(db)

    def run(self, organization_id: str, fundraising_duration_months: Decimal = Decimal("5"), buffer_months: Decimal = Decimal("2")) -> dict:
        start = time.perf_counter()
        run = self.workflow_repo.start(
            organization_id,
            "fundraising_timing_workflow",
            {"fundraising_duration_months": str(fundraising_duration_months), "buffer_months": str(buffer_months)},
        )
        facts = self.finance_repo.latest_fact_map(organization_id)
        org = OrganizationRepository(self.db).get(organization_id)
        runway = Decimal(str(facts["runway_months"].value))
        threshold = fundraising_duration_months + buffer_months
        should_start = runway <= threshold
        self.workflow_repo.step(run.id, "compare_to_raise_timeline", {"runway": str(runway)}, {"threshold": str(threshold), "should_start": should_start})
        if should_start:
            rec = Recommendation(
                organization_id=organization_id,
                user_type=org.user_type if org else "startup",
                stable_key="fundraising_timing",
                title="Start fundraising now",
                description="Runway is below the raise duration plus operating buffer.",
                issue=f"Runway is {runway} months and threshold is {threshold} months.",
                impact="Fundraising lead time plus buffer exceeds available runway.",
                recommended_action="Start investor outreach this week.",
                confidence_score=Decimal("0.9"),
                impact_metric="runway_months",
                primary_cta="Open fundraising plan",
                secondary_cta="View audit",
                evidence=[{"source_type": "financial_fact", "source_id": facts["runway_months"].id, "title": "Runway", "excerpt": facts["runway_months"].formula}],
                source_fact_ids=[facts["runway_months"].id],
            )
            alert = Alert(organization_id=organization_id, severity="high", title="Fundraising timing risk", message=rec.issue, evidence=rec.evidence)
            existing = self.db.scalar(select(Recommendation).where(Recommendation.organization_id == organization_id, Recommendation.stable_key == rec.stable_key))
            if existing is None:
                self.db.add(rec)
            elif existing.status not in {"approved", "dismissed", "completed"}:
                existing.title = rec.title
                existing.description = rec.description
                existing.issue = rec.issue
                existing.impact = rec.impact
                existing.recommended_action = rec.recommended_action
                existing.evidence = rec.evidence
                existing.source_fact_ids = rec.source_fact_ids
                existing.status = "active"
            self.db.add(alert)
            self.db.flush()
        self.workflow_repo.finish(run, {"should_start": should_start, "runway": str(runway), "threshold": str(threshold)}, duration_ms=int((time.perf_counter() - start) * 1000))
        self.db.commit()
        return {"workflow_run_id": run.id, "should_start": should_start, "runway": str(runway), "threshold": str(threshold)}

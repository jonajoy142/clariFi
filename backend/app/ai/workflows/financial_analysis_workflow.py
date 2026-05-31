import time
from sqlalchemy.orm import Session

from app.models.finance import CFOMemo
from app.repositories.finance import AuditRepository, FinanceRepository, RecommendationRepository, WorkflowRepository
from app.services.facts import FinancialFactService
from app.services.recommendations import RecommendationService


class FinancialAnalysisWorkflow:
    def __init__(self, db: Session):
        self.db = db
        self.workflow_repo = WorkflowRepository(db)
        self.finance_repo = FinanceRepository(db)
        self.rec_repo = RecommendationRepository(db)
        self.audit_repo = AuditRepository(db)

    def run(self, organization_id: str) -> dict:
        start = time.perf_counter()
        run = self.workflow_repo.start(organization_id, "financial_analysis_workflow", {})
        facts = FinancialFactService(self.db).calculate_and_persist(organization_id)
        self.workflow_repo.step(run.id, "calculate_facts", {}, {"fact_count": len(facts)})
        recommendations = RecommendationService(self.db).regenerate(organization_id)
        self.workflow_repo.step(run.id, "generate_recommendations", {}, {"recommendation_count": len(recommendations)})
        memo = CFOMemo(
            organization_id=organization_id,
            title="Daily CFO briefing",
            summary=f"Generated from {len(facts)} verified financial facts and {len(recommendations)} open recommendations.",
            risks=[{"title": rec.title, "issue": rec.issue, "impact": rec.impact} for rec in recommendations[:3]],
            actions=[{"title": rec.title, "recommended_action": rec.recommended_action} for rec in recommendations[:3]],
            source_fact_ids=[fact.id for fact in facts],
        )
        self.db.add(memo)
        self.db.flush()
        self.workflow_repo.step(run.id, "create_cfo_memo", {}, {"memo_id": memo.id})
        self.workflow_repo.finish(run, {"memo_id": memo.id}, duration_ms=int((time.perf_counter() - start) * 1000))
        self.db.commit()
        return {"workflow_run_id": run.id, "memo_id": memo.id}


from sqlalchemy.orm import Session

from app.repositories.finance import FinanceRepository, OrganizationRepository, RecommendationRepository
from app.services.facts import FinancialFactService
from app.services.recommendations import RecommendationService


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.finance_repo = FinanceRepository(db)
        self.rec_repo = RecommendationRepository(db)

    def summary(self, organization_id: str) -> dict:
        org = self.org_repo.get(organization_id)
        if org is None:
            raise ValueError("Organization not found")
        if not self.finance_repo.facts(organization_id):
            FinancialFactService(self.db).calculate_and_persist(organization_id)
            RecommendationService(self.db).regenerate(organization_id)
            self.db.commit()

        facts = list(self.finance_repo.facts(organization_id))
        fact_map = {fact.fact_type: fact for fact in facts}
        recommendations = list(self.rec_repo.list(organization_id, status="active"))
        alerts = list(self.rec_repo.alerts(organization_id))
        metrics = {
            "current_cash": _value(fact_map, "current_cash"),
            "monthly_burn": _value(fact_map, "monthly_burn"),
            "runway_months": _value(fact_map, "runway_months"),
            "receivables": _value(fact_map, "total_receivables"),
            "overdue_receivables": _value(fact_map, "overdue_receivables"),
            "payables_30d": _value(fact_map, "upcoming_payables_30d"),
            "risk_score": _risk_score(_value(fact_map, "runway_months"), _value(fact_map, "overdue_receivables")),
        }
        return {
            "organization": {
                "id": org.id,
                "name": org.name,
                "user_type": org.user_type,
                "currency": org.currency,
                "settings": org.settings or {},
            },
            "metrics": metrics,
            "top_risks": [{"title": alert.title, "message": alert.message, "severity": alert.severity} for alert in alerts[:3]],
            "recommended_actions": [
                {
                    "id": rec.id,
                    "title": rec.title,
                    "impact": rec.impact,
                    "recommended_action": rec.recommended_action,
                    "confidence_score": float(rec.confidence_score),
                }
                for rec in recommendations[:3]
            ],
            "facts": [_fact_dict(fact) for fact in facts],
        }


def _value(facts: dict, key: str) -> float:
    fact = facts.get(key)
    return float(fact.value) if fact else 0.0


def _risk_score(runway_months: float, overdue_receivables: float) -> int:
    score = 20
    if runway_months < 6:
        score += 55
    elif runway_months < 9:
        score += 35
    elif runway_months < 12:
        score += 18
    if overdue_receivables > 100000:
        score += 15
    elif overdue_receivables > 0:
        score += 8
    return min(score, 100)


def _fact_dict(fact) -> dict:
    return {
        "id": fact.id,
        "fact_type": fact.fact_type,
        "value": float(fact.value),
        "currency": fact.currency,
        "formula": fact.formula,
        "engine_name": fact.engine_name,
        "engine_version": fact.engine_version,
        "source_record_ids": fact.source_record_ids,
        "audit_log_id": fact.audit_log_id,
        "created_at": fact.created_at.isoformat(),
    }

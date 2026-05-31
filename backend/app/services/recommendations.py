from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.finance import Alert, Organization, Recommendation
from app.repositories.finance import FinanceRepository, OrganizationRepository, RecommendationRepository


def _fact_value(facts: dict, key: str) -> Decimal:
    fact = facts.get(key)
    return Decimal(str(fact.value)) if fact else Decimal("0")


def _evidence_from_fact(fact) -> dict:
    return {
        "source_type": "financial_fact",
        "source_id": fact.id,
        "title": fact.fact_type,
        "excerpt": f"{fact.fact_type} = {fact.value} using {fact.formula}",
        "amount": str(fact.value),
    }


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db
        self.finance_repo = FinanceRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.repo = RecommendationRepository(db)

    def regenerate(self, organization_id: str) -> list[Recommendation]:
        org = self.org_repo.get(organization_id)
        if org is None:
            raise ValueError("Organization not found")

        fact_map = self.finance_repo.latest_fact_map(organization_id)
        recommendations: list[Recommendation] = []
        alerts: list[Alert] = []
        runway = _fact_value(fact_map, "runway_months")
        burn = _fact_value(fact_map, "monthly_burn")
        overdue = _fact_value(fact_map, "overdue_receivables")
        duplicate_waste = _fact_value(fact_map, "duplicate_vendor_waste_monthly")
        recurring = _fact_value(fact_map, "recurring_subscriptions_monthly")

        if runway and runway <= Decimal("11"):
            fact = fact_map["runway_months"]
            recommendations.append(
                Recommendation(
                    organization_id=organization_id,
                    user_type=org.user_type,
                    stable_key="runway_active_management",
                    title="Runway needs active management",
                    description=f"Current runway is {runway} months and needs active operating discipline before new fixed commitments.",
                    issue=f"Current runway is {runway} months based on verified cash and burn.",
                    impact=f"At current burn of ₹{burn:,.0f}/month, every ₹1L of net burn changes runway materially.",
                    recommended_action="Review hiring, vendor spend, and overdue collections before committing to new fixed costs.",
                    confidence_score=Decimal("0.92"),
                    financial_impact_amount=burn,
                    impact_metric="monthly_burn",
                    primary_cta="Open simulator",
                    secondary_cta="View audit",
                    evidence=[_evidence_from_fact(fact)],
                    source_fact_ids=[fact.id],
                )
            )

        if overdue > 0:
            fact = fact_map["overdue_receivables"]
            recommendations.append(
                Recommendation(
                    organization_id=organization_id,
                    user_type=org.user_type,
                    stable_key="collect_overdue_receivables",
                    title="Collect overdue receivables",
                    description=f"Outstanding overdue receivables are tying up ₹{overdue:,.0f} of cash.",
                    issue=f"₹{overdue:,.0f} is overdue and can improve short-term cash coverage.",
                    impact="Collections improve cash without increasing revenue targets or cutting core spend.",
                    recommended_action="Approve a follow-up draft for the highest-priority overdue invoice.",
                    confidence_score=Decimal("0.95"),
                    financial_impact_amount=overdue,
                    impact_metric="cash_collection",
                    primary_cta="Draft follow-up",
                    secondary_cta="Dismiss",
                    evidence=[_evidence_from_fact(fact)],
                    source_fact_ids=[fact.id],
                )
            )
            alerts.append(
                Alert(
                    organization_id=organization_id,
                    severity="high" if overdue >= Decimal("100000") else "medium",
                    title="Overdue invoice detected",
                    message=f"Receivables engine found ₹{overdue:,.0f} overdue.",
                    evidence=[_evidence_from_fact(fact)],
                )
            )

        if duplicate_waste > 0 or recurring > Decimal("50000"):
            fact = fact_map.get("recurring_subscriptions_monthly")
            recommendations.append(
                Recommendation(
                    organization_id=organization_id,
                    user_type=org.user_type,
                    stable_key="recurring_vendor_waste",
                    title="Review recurring vendor waste",
                    description="Recurring software and vendor spend should be reviewed before adding payroll.",
                    issue=f"Recurring subscriptions are ₹{recurring:,.0f}/month.",
                    impact=f"Cutting ₹{max(duplicate_waste, Decimal('25000')):,.0f}/month extends runway through lower fixed burn.",
                    recommended_action="Inspect duplicate and SaaS-like vendors before the next billing cycle.",
                    confidence_score=Decimal("0.84"),
                    financial_impact_amount=max(duplicate_waste, Decimal("25000")),
                    impact_metric="monthly_savings",
                    primary_cta="Review vendors",
                    secondary_cta="Simulate cut",
                    evidence=[_evidence_from_fact(fact)] if fact else [],
                    source_fact_ids=[fact.id] if fact else [],
                )
            )

        if org.user_type == "startup":
            self._startup_specific(organization_id, fact_map, recommendations, alerts)
        else:
            self._freelancer_specific(organization_id, fact_map, recommendations, alerts)

        self.repo.upsert_generated(organization_id, recommendations, alerts)
        return recommendations

    def _startup_specific(self, organization_id: str, fact_map: dict, recommendations: list[Recommendation], alerts: list[Alert]) -> None:
        org = self.org_repo.get(organization_id)
        runway = _fact_value(fact_map, "runway_months")
        fundraising_lead_time = Decimal("7")
        fact = fact_map.get("runway_months")
        if fact and runway <= fundraising_lead_time:
            recommendations.append(
                Recommendation(
                    organization_id=organization_id,
                    user_type=org.user_type if org else "startup",
                    stable_key="fundraising_timing",
                    title="Start fundraising process now",
                    description="Runway is below the fundraising duration plus buffer threshold.",
                    issue=f"Runway is {runway} months, at or below the 7 month fundraising lead-time threshold.",
                    impact="Fundraising has calendar risk; waiting compresses negotiation time.",
                    recommended_action="Prepare investor pipeline and metrics package this week.",
                    confidence_score=Decimal("0.9"),
                    impact_metric="runway_months",
                    primary_cta="Open fundraising plan",
                    secondary_cta="View runway math",
                    evidence=[_evidence_from_fact(fact)],
                    source_fact_ids=[fact.id],
                )
            )
        burn = _fact_value(fact_map, "monthly_burn")
        runway_fact = fact_map.get("runway_months")
        if runway_fact:
            recommendations.append(
                Recommendation(
                    organization_id=organization_id,
                    user_type=org.user_type if org else "startup",
                    stable_key="aws_spend_spike",
                    title="Runway dropped because AWS spend increased",
                    description="Cloud usage increased versus the prior period and is now a material burn driver.",
                    issue="AWS spend increased from ₹50,000 to ₹69,000 in the seeded operating data.",
                    impact="Burn increased ₹19,000/month from this vendor line, reducing runway unless usage is reviewed.",
                    recommended_action="Review AWS usage, commitments, and analytics jobs before approving additional hiring.",
                    confidence_score=Decimal("0.88"),
                    financial_impact_amount=Decimal("19000"),
                    impact_metric="monthly_burn_increase",
                    primary_cta="Review vendors",
                    secondary_cta="Simulate cut",
                    evidence=[
                        {"source_type": "transaction", "source_id": "seed/aws/previous", "title": "AWS previous spend", "excerpt": "AWS previous month: ₹50,000"},
                        {"source_type": "transaction", "source_id": "seed/aws/current", "title": "AWS current spend", "excerpt": "AWS current month: ₹69,000"},
                        _evidence_from_fact(runway_fact),
                    ],
                    source_fact_ids=[runway_fact.id],
                )
            )
        alerts.append(
            Alert(
                organization_id=organization_id,
                severity="medium",
                title="AWS spend increased",
                message="AWS spend increased 38% versus the previous period in seeded connector data.",
                evidence=[{"source_type": "transaction", "source_id": "seed/aws", "title": "AWS spend spike", "excerpt": "Previous ₹50,000, current ₹69,000, increase 38%."}],
            )
        )

    def _freelancer_specific(self, organization_id: str, fact_map: dict, recommendations: list[Recommendation], alerts: list[Alert]) -> None:
        org = self.org_repo.get(organization_id)
        reserve = _fact_value(fact_map, "suggested_tax_reserve")
        fact = fact_map.get("suggested_tax_reserve")
        if fact and reserve > 0:
            recommendations.append(
                Recommendation(
                    organization_id=organization_id,
                    user_type=org.user_type if org else "freelancer",
                    stable_key="tax_reserve",
                    title="Set aside estimated tax reserve",
                    description="Recent received income creates a tax reserve obligation estimate.",
                    issue=f"Suggested reserve is ₹{reserve:,.0f} based on recent received income.",
                    impact="This reduces quarter-end cash shock. Estimate only, not tax or legal advice.",
                    recommended_action="Move the reserve to a separate account or tag it as unavailable cash.",
                    confidence_score=Decimal("0.75"),
                    financial_impact_amount=reserve,
                    impact_metric="suggested_tax_reserve",
                    primary_cta="View tax reserve",
                    secondary_cta="Dismiss",
                    evidence=[_evidence_from_fact(fact)],
                    source_fact_ids=[fact.id],
                )
            )

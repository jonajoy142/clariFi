from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.engines.hiring_scenario import HiringScenarioEngine
from app.engines.runway import RunwayEngine
from app.repositories.finance import FinanceRepository


class SimulationService:
    def __init__(self, db: Session):
        self.db = db
        self.finance_repo = FinanceRepository(db)

    def hiring(
        self,
        organization_id: str,
        monthly_cost: Decimal,
        role: str,
        *,
        benefits_multiplier: Decimal = Decimal("1.18"),
        equipment_cost: Decimal = Decimal("120000"),
        software_seat_cost: Decimal = Decimal("12000"),
        recruiting_onboarding_cost: Decimal = Decimal("50000"),
        start_date: date | None = None,
    ) -> dict:
        facts = self.finance_repo.latest_fact_map(organization_id)
        current_cash = Decimal(str(facts["current_cash"].value))
        monthly_burn = Decimal(str(facts["monthly_burn"].value))
        payroll_increase = (monthly_cost * benefits_multiplier) + software_seat_cost
        one_time_cost = equipment_cost + recruiting_onboarding_cost
        effective_cash = current_cash - one_time_cost
        result = HiringScenarioEngine().calculate(effective_cash, monthly_burn, payroll_increase)
        before = HiringScenarioEngine().calculate(current_cash, monthly_burn, Decimal("0"))
        daily_delta = payroll_increase / Decimal("30")
        return {
            **result,
            "runway_before": before["runway_before"],
            "base_salary": monthly_cost,
            "benefits_multiplier": benefits_multiplier,
            "monthly_payroll_increase": payroll_increase,
            "equipment_cost": equipment_cost,
            "software_seat_cost": software_seat_cost,
            "recruiting_onboarding_cost": recruiting_onboarding_cost,
            "one_time_cost": one_time_cost,
            "start_date": (start_date or date.today()).isoformat(),
            "cash_after_one_time_cost": effective_cash,
            "cash_impact_30d": one_time_cost + (daily_delta * Decimal("30")),
            "cash_impact_60d": one_time_cost + (daily_delta * Decimal("60")),
            "cash_impact_90d": one_time_cost + (daily_delta * Decimal("90")),
            "evidence": [
                _fact_evidence(facts["current_cash"]),
                _fact_evidence(facts["monthly_burn"]),
                {"source_type": "user_input", "source_id": "simulate/hiring", "title": f"Hire {role}", "excerpt": f"Base salary ₹{monthly_cost:,.0f}, benefits multiplier {benefits_multiplier}, one-time setup ₹{one_time_cost:,.0f}"},
            ],
        }

    def vendor_cut(self, organization_id: str, monthly_savings: Decimal, vendor_name: str, cancellation_date: date | str | None = None, operational_risk_note: str = "Review owner impact before cancelling.") -> dict:
        facts = self.finance_repo.latest_fact_map(organization_id)
        current_cash = Decimal(str(facts["current_cash"].value))
        monthly_burn = Decimal(str(facts["monthly_burn"].value))
        result = RunwayEngine().scenario(current_cash, monthly_burn, -monthly_savings)
        risk_level = "improved" if result["runway_after"] > result["runway_before"] else "unchanged"
        return {
            **result,
            "risk_level": risk_level,
            "vendor_name": vendor_name,
            "monthly_cost": monthly_savings,
            "cancellation_date": _date_string(cancellation_date),
            "operational_risk_note": operational_risk_note,
            "evidence": [
                _fact_evidence(facts["current_cash"]),
                _fact_evidence(facts["monthly_burn"]),
                {"source_type": "user_input", "source_id": "simulate/vendor-cut", "title": vendor_name, "excerpt": f"Monthly savings ₹{monthly_savings:,.0f}"},
            ],
        }

    def invoice_collection(self, organization_id: str, invoice_id: str | None, expected_payment_date: date | str | None, probability: Decimal) -> dict:
        invoices = [invoice for invoice in self.finance_repo.invoices(organization_id) if invoice.direction == "receivable" and invoice.status != "paid"]
        invoice = next((item for item in invoices if item.id == invoice_id), invoices[0] if invoices else None)
        if invoice is None:
            return {"error": "No receivable invoice available for simulation"}
        amount = Decimal(str(invoice.amount)) - Decimal(str(invoice.paid_amount))
        expected_value = amount * probability
        facts = self.finance_repo.latest_fact_map(organization_id)
        current_cash = Decimal(str(facts["current_cash"].value))
        return {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "amount": amount,
            "expected_payment_date": _date_string(expected_payment_date),
            "probability": probability,
            "expected_cash_impact": expected_value,
            "cash_before": current_cash,
            "cash_after_expected_collection": current_cash + expected_value,
            "evidence": [_fact_evidence(facts["current_cash"]), {"source_type": "invoice", "source_id": invoice.id, "title": invoice.invoice_number, "excerpt": f"Invoice amount ₹{amount:,.0f}, due {invoice.due_on.isoformat()}"}],
        }


def _fact_evidence(fact) -> dict:
    return {
        "source_type": "financial_fact",
        "source_id": fact.id,
        "title": fact.fact_type,
        "excerpt": f"{fact.fact_type}: ₹{float(fact.value):,.0f}. Formula: {fact.formula}",
        "amount": str(fact.value),
    }


def _date_string(value: date | str | None) -> str:
    if value is None:
        return date.today().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)

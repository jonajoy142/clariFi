from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.ai.tools.base import Tool, ToolRegistry, ToolRuntime
from app.repositories.finance import FinanceRepository
from app.services.documents import DocumentService
from app.services.facts import FinancialFactService
from app.services.simulation import SimulationService


class EmptyInput(BaseModel):
    pass


class QueryInput(BaseModel):
    query: str


class HiringInput(BaseModel):
    role: str = "Engineer"
    monthly_cost: Decimal = Field(..., gt=0)


class VendorCutInput(BaseModel):
    vendor_name: str
    monthly_savings: Decimal = Field(..., gt=0)


class DraftEmailInput(BaseModel):
    customer_name: str
    invoice_number: str
    amount: Decimal
    days_overdue: int


class CalculateRunwayTool(Tool):
    name = "calculate_runway"
    description = "Return verified current cash, monthly burn, and runway facts."
    input_schema = EmptyInput

    def execute(self, runtime: ToolRuntime, payload: EmptyInput) -> dict[str, Any]:
        FinancialFactService(runtime.db).calculate_and_persist(runtime.organization_id)
        facts = FinanceRepository(runtime.db).latest_fact_map(runtime.organization_id)
        return _select_facts(facts, ["current_cash", "monthly_burn", "runway_months"])


class CalculateBurnTool(Tool):
    name = "calculate_burn"
    description = "Return verified burn rate and category facts."
    input_schema = EmptyInput

    def execute(self, runtime: ToolRuntime, payload: EmptyInput) -> dict[str, Any]:
        FinancialFactService(runtime.db).calculate_and_persist(runtime.organization_id)
        facts = FinanceRepository(runtime.db).latest_fact_map(runtime.organization_id)
        return _select_facts(facts, ["monthly_burn", "burn_trend_percent", "recurring_subscriptions_monthly"])


class CalculateReceivablesTool(Tool):
    name = "calculate_receivables"
    description = "Return verified receivable and overdue invoice facts."
    input_schema = EmptyInput

    def execute(self, runtime: ToolRuntime, payload: EmptyInput) -> dict[str, Any]:
        FinancialFactService(runtime.db).calculate_and_persist(runtime.organization_id)
        facts = FinanceRepository(runtime.db).latest_fact_map(runtime.organization_id)
        return _select_facts(facts, ["total_receivables", "overdue_receivables", "expected_collection_amount"])


class EmployeeCountTool(Tool):
    name = "count_employees"
    description = "Count active payroll items and return roles and monthly payroll."
    input_schema = EmptyInput

    def execute(self, runtime: ToolRuntime, payload: EmptyInput) -> dict[str, Any]:
        payroll = [item for item in FinanceRepository(runtime.db).payroll(runtime.organization_id) if item.active]
        total = sum((Decimal(str(item.monthly_cost)) for item in payroll), Decimal("0"))
        return {
            "employee_count": len(payroll),
            "monthly_payroll": str(total),
            "roles": [{"name": item.employee_name, "role": item.role, "monthly_cost": str(item.monthly_cost)} for item in payroll],
            "evidence": [{"source_type": "payroll_item", "source_id": item.id, "title": item.employee_name, "excerpt": f"{item.role}: ₹{Decimal(str(item.monthly_cost)):,.0f}/month"} for item in payroll],
        }


class BurnBreakdownTool(Tool):
    name = "calculate_burn_breakdown"
    description = "Break burn into payroll, vendors, subscriptions, taxes, and other operating expenses."
    input_schema = EmptyInput

    def execute(self, runtime: ToolRuntime, payload: EmptyInput) -> dict[str, Any]:
        repo = FinanceRepository(runtime.db)
        transactions = [txn for txn in repo.transactions(runtime.organization_id) if Decimal(str(txn.amount)) < 0]
        payroll_items = [item for item in repo.payroll(runtime.organization_id) if item.active]
        subscriptions = repo.subscriptions(runtime.organization_id)
        payroll = sum((Decimal(str(item.monthly_cost)) for item in payroll_items), Decimal("0"))
        subscription_total = sum((Decimal(str(sub.monthly_amount)) for sub in subscriptions if sub.status == "active"), Decimal("0"))
        taxes = abs(sum((Decimal(str(txn.amount)) for txn in transactions if "tax" in txn.category.lower()), Decimal("0")))
        vendor_expense = abs(sum((Decimal(str(txn.amount)) for txn in transactions if txn.vendor_id and "tax" not in txn.category.lower()), Decimal("0")))
        other = abs(sum((Decimal(str(txn.amount)) for txn in transactions if not txn.vendor_id and "tax" not in txn.category.lower()), Decimal("0")))
        total = payroll + vendor_expense + subscription_total + taxes + other
        categories = {
            "payroll": payroll,
            "vendors": vendor_expense,
            "subscriptions": subscription_total,
            "taxes": taxes,
            "other_operating_expenses": other,
        }
        return {
            "total_burn_basis": str(total),
            "categories": {
                key: {
                    "amount": str(value),
                    "percentage": str((value / total * Decimal("100")).quantize(Decimal("0.01")) if total else Decimal("0")),
                }
                for key, value in categories.items()
            },
            "evidence": [
                {"source_type": "payroll", "source_id": "payroll_items", "title": "Active payroll", "excerpt": f"{len(payroll_items)} active payroll items total ₹{payroll:,.0f}/month"},
                {"source_type": "subscription", "source_id": "subscriptions", "title": "Active subscriptions", "excerpt": f"{len(subscriptions)} subscriptions total ₹{subscription_total:,.0f}/month"},
            ],
        }


class ReceivablesDetailTool(Tool):
    name = "list_receivables"
    description = "List unpaid receivables with client, invoice, amount, due date, days overdue, and priority."
    input_schema = EmptyInput

    def execute(self, runtime: ToolRuntime, payload: EmptyInput) -> dict[str, Any]:
        repo = FinanceRepository(runtime.db)
        customers = {customer.id: customer for customer in repo.customers(runtime.organization_id)}
        today = date.today()
        rows = []
        for invoice in repo.invoices(runtime.organization_id):
            if invoice.direction != "receivable" or invoice.status == "paid":
                continue
            outstanding = Decimal(str(invoice.amount)) - Decimal(str(invoice.paid_amount))
            days_overdue = max(0, (today - invoice.due_on).days)
            customer = customers.get(invoice.customer_id)
            rows.append({
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "customer_name": customer.name if customer else "Unknown client",
                "customer_email": customer.email if customer else None,
                "amount": str(outstanding),
                "due_on": invoice.due_on.isoformat(),
                "days_overdue": days_overdue,
                "priority": "high" if days_overdue >= 14 else "normal",
                "suggested_action": "Send firm follow-up" if days_overdue >= 14 else "Monitor",
            })
        return {"receivables": rows, "total_unpaid": str(sum((Decimal(row["amount"]) for row in rows), Decimal("0")))}


class TaxReserveTool(Tool):
    name = "calculate_tax_reserve"
    description = "Return deterministic freelancer tax reserve estimate facts."
    input_schema = EmptyInput

    def execute(self, runtime: ToolRuntime, payload: EmptyInput) -> dict[str, Any]:
        FinancialFactService(runtime.db).calculate_and_persist(runtime.organization_id)
        facts = FinanceRepository(runtime.db).latest_fact_map(runtime.organization_id)
        return _select_facts(facts, ["income_received_90d", "suggested_tax_reserve"])


class CashGapTool(Tool):
    name = "calculate_cash_gap"
    description = "Return cash gap risk using current cash, burn, forecast, and receivable facts."
    input_schema = EmptyInput

    def execute(self, runtime: ToolRuntime, payload: EmptyInput) -> dict[str, Any]:
        FinancialFactService(runtime.db).calculate_and_persist(runtime.organization_id)
        facts = FinanceRepository(runtime.db).latest_fact_map(runtime.organization_id)
        current_cash = Decimal(str(facts.get("current_cash").value)) if facts.get("current_cash") else Decimal("0")
        monthly_burn = Decimal(str(facts.get("monthly_burn").value)) if facts.get("monthly_burn") else Decimal("0")
        overdue = Decimal(str(facts.get("overdue_receivables").value)) if facts.get("overdue_receivables") else Decimal("0")
        days_until_shortage = Decimal("999") if monthly_burn <= 0 else (current_cash / (monthly_burn / Decimal("30"))).quantize(Decimal("0.01"))
        risk = "high" if days_until_shortage < 45 else "medium" if days_until_shortage < 90 else "low"
        return {
            **_select_facts(facts, ["current_cash", "monthly_burn", "overdue_receivables", "projected_cash_30d", "projected_cash_60d", "projected_cash_90d"]),
            "days_until_cash_shortage": str(days_until_shortage),
            "cash_gap_risk": risk,
            "overdue_invoice_cash_impact": str(overdue),
        }


class SimulateHiringTool(Tool):
    name = "simulate_hiring"
    description = "Simulate hiring impact using deterministic runway math."
    input_schema = HiringInput

    def execute(self, runtime: ToolRuntime, payload: HiringInput) -> dict[str, Any]:
        return SimulationService(runtime.db).hiring(runtime.organization_id, payload.monthly_cost, payload.role)


class SimulateVendorCutTool(Tool):
    name = "simulate_vendor_cut"
    description = "Simulate runway impact from cutting vendor spend."
    input_schema = VendorCutInput

    def execute(self, runtime: ToolRuntime, payload: VendorCutInput) -> dict[str, Any]:
        return SimulationService(runtime.db).vendor_cut(runtime.organization_id, payload.monthly_savings, payload.vendor_name)


class RetrieveEvidenceTool(Tool):
    name = "retrieve_evidence"
    description = "Retrieve semantic document evidence. Never used for math."
    input_schema = QueryInput

    def execute(self, runtime: ToolRuntime, payload: QueryInput) -> dict[str, Any]:
        return {"items": DocumentService(runtime.db).search(runtime.organization_id, payload.query)}


class DraftEmailTool(Tool):
    name = "draft_email"
    description = "Create a draft follow-up email. It never sends email."
    input_schema = DraftEmailInput

    def execute(self, runtime: ToolRuntime, payload: DraftEmailInput) -> dict[str, Any]:
        body = (
            f"Subject: Follow-up on invoice {payload.invoice_number}\n\n"
            f"Hi {payload.customer_name},\n\n"
            f"Checking in on invoice {payload.invoice_number} for ₹{payload.amount:,.0f}, "
            f"which is {payload.days_overdue} days overdue. Could you confirm the expected payment date?\n\n"
            "Thanks."
        )
        return {
            "action_type": "email_draft",
            "title": f"Follow up with {payload.customer_name}",
            "body": body,
            "requires_approval": True,
        }


class CreateTaskTool(Tool):
    name = "create_task"
    description = "Create a draft operational task."
    input_schema = QueryInput

    def execute(self, runtime: ToolRuntime, payload: QueryInput) -> dict[str, Any]:
        return {"status": "draft", "title": payload.query, "requires_approval": True}


class CreateAlertTool(Tool):
    name = "create_alert"
    description = "Create alert payload for user review."
    input_schema = QueryInput

    def execute(self, runtime: ToolRuntime, payload: QueryInput) -> dict[str, Any]:
        return {"status": "draft", "message": payload.query}


def build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in [
        CalculateRunwayTool(),
        CalculateBurnTool(),
        CalculateReceivablesTool(),
        EmployeeCountTool(),
        BurnBreakdownTool(),
        ReceivablesDetailTool(),
        TaxReserveTool(),
        CashGapTool(),
        SimulateHiringTool(),
        SimulateVendorCutTool(),
        RetrieveEvidenceTool(),
        DraftEmailTool(),
        CreateTaskTool(),
        CreateAlertTool(),
    ]:
        registry.register(tool)
    return registry


def _select_facts(facts: dict, keys: list[str]) -> dict[str, Any]:
    return {
        key: {
            "id": facts[key].id,
            "value": str(facts[key].value),
            "formula": facts[key].formula,
            "engine_name": facts[key].engine_name,
            "source_record_ids": facts[key].source_record_ids,
            "audit_log_id": facts[key].audit_log_id,
        }
        for key in keys
        if key in facts
    }

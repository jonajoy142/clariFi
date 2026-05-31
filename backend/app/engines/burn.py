from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.engines.base import EngineOutput, FactResult, money


class BurnEngine:
    name = "BurnEngine"
    version = "1.0.0"

    def calculate(self, transactions: list, payroll_items: list, as_of: date | None = None) -> EngineOutput:
        as_of = as_of or date.today()
        start = as_of - timedelta(days=30)
        trailing_expenses = [
            txn for txn in transactions
            if start <= txn.occurred_on <= as_of and money(txn.amount) < 0
        ]
        expense_total = abs(sum((money(txn.amount) for txn in trailing_expenses), Decimal("0.00")))
        active_payroll = sum((money(item.monthly_cost) for item in payroll_items if item.active), Decimal("0.00"))
        monthly_burn = money(expense_total + active_payroll)
        category_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        for txn in trailing_expenses:
            category_totals[txn.category] += abs(money(txn.amount))

        previous_start = as_of - timedelta(days=60)
        previous_expenses = [
            txn for txn in transactions
            if previous_start <= txn.occurred_on < start and money(txn.amount) < 0
        ]
        previous_total = abs(sum((money(txn.amount) for txn in previous_expenses), Decimal("0.00")))
        trend = Decimal("0.00")
        if previous_total:
            trend = ((expense_total - previous_total) / previous_total * Decimal("100")).quantize(Decimal("0.01"))

        return EngineOutput(
            engine_name=self.name,
            engine_version=self.version,
            facts=[
                FactResult(
                    fact_type="monthly_burn",
                    value=monthly_burn,
                    formula="abs(sum(expense transactions in trailing 30 days)) + active monthly payroll",
                    source_record_ids=[txn.id for txn in trailing_expenses] + [item.id for item in payroll_items if item.active],
                    period_start=start,
                    period_end=as_of,
                ),
                FactResult(
                    fact_type="burn_trend_percent",
                    value=trend,
                    formula="(trailing_30d_expense - previous_30d_expense) / previous_30d_expense * 100",
                    source_record_ids=[txn.id for txn in trailing_expenses + previous_expenses],
                    period_start=previous_start,
                    period_end=as_of,
                ),
            ],
            details={"expense_categories": {key: float(value) for key, value in category_totals.items()}},
        )


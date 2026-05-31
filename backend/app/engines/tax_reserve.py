from datetime import date, timedelta
from decimal import Decimal

from app.engines.base import EngineOutput, FactResult, money


class TaxReserveEngine:
    name = "TaxReserveEngine"
    version = "1.0.0"

    def calculate(self, transactions: list, reserve_percentage: Decimal = Decimal("0.25"), as_of: date | None = None) -> EngineOutput:
        as_of = as_of or date.today()
        start = as_of - timedelta(days=90)
        income_transactions = [
            txn for txn in transactions
            if start <= txn.occurred_on <= as_of and money(txn.amount) > 0 and txn.category in {"revenue", "client_payment", "stripe_revenue", "razorpay_revenue"}
        ]
        income_received = sum((money(txn.amount) for txn in income_transactions), Decimal("0.00"))
        reserve = income_received * reserve_percentage
        return EngineOutput(
            engine_name=self.name,
            engine_version=self.version,
            facts=[
                FactResult(
                    fact_type="income_received_90d",
                    value=money(income_received),
                    formula="sum(income transactions in trailing 90 days)",
                    source_record_ids=[txn.id for txn in income_transactions],
                    period_start=start,
                    period_end=as_of,
                ),
                FactResult(
                    fact_type="suggested_tax_reserve",
                    value=money(reserve),
                    formula=f"income_received_90d * configurable reserve percentage {reserve_percentage}",
                    source_record_ids=[txn.id for txn in income_transactions],
                    period_start=start,
                    period_end=as_of,
                    confidence_score=Decimal("0.75"),
                ),
            ],
            details={"reserve_percentage": float(reserve_percentage), "disclaimer": "Estimate only, not tax or legal advice."},
        )


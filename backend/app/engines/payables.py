from datetime import date, timedelta
from decimal import Decimal

from app.engines.base import EngineOutput, FactResult, money


class PayablesEngine:
    name = "PayablesEngine"
    version = "1.0.0"

    def calculate(self, invoices: list, as_of: date | None = None) -> EngineOutput:
        as_of = as_of or date.today()
        horizon = as_of + timedelta(days=30)
        upcoming = [
            invoice for invoice in invoices
            if invoice.direction == "payable" and invoice.status != "paid" and as_of <= invoice.due_on <= horizon
        ]
        total = sum((money(invoice.amount) - money(invoice.paid_amount) for invoice in upcoming), Decimal("0.00"))
        return EngineOutput(
            engine_name=self.name,
            engine_version=self.version,
            facts=[
                FactResult(
                    fact_type="upcoming_payables_30d",
                    value=money(total),
                    formula="sum(payable invoice outstanding where due_on within 30 days)",
                    source_record_ids=[invoice.id for invoice in upcoming],
                    period_start=as_of,
                    period_end=horizon,
                )
            ],
            details={"upcoming_bills": [invoice.invoice_number for invoice in upcoming]},
        )


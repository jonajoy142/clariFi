from datetime import date
from decimal import Decimal

from app.engines.base import EngineOutput, FactResult, money


class ReceivablesEngine:
    name = "ReceivablesEngine"
    version = "1.0.0"

    def calculate(self, invoices: list, as_of: date | None = None) -> EngineOutput:
        as_of = as_of or date.today()
        receivables = [invoice for invoice in invoices if invoice.direction == "receivable" and invoice.status != "paid"]
        total_outstanding = sum((money(invoice.amount) - money(invoice.paid_amount) for invoice in receivables), Decimal("0.00"))
        overdue = [invoice for invoice in receivables if invoice.due_on < as_of]
        overdue_total = sum((money(invoice.amount) - money(invoice.paid_amount) for invoice in overdue), Decimal("0.00"))
        expected_collection = total_outstanding * Decimal("0.85")
        days_overdue = {
            invoice.invoice_number: max(0, (as_of - invoice.due_on).days)
            for invoice in overdue
        }

        return EngineOutput(
            engine_name=self.name,
            engine_version=self.version,
            facts=[
                FactResult(
                    fact_type="total_receivables",
                    value=money(total_outstanding),
                    formula="sum(receivable invoice.amount - paid_amount where status != paid)",
                    source_record_ids=[invoice.id for invoice in receivables],
                    period_end=as_of,
                ),
                FactResult(
                    fact_type="overdue_receivables",
                    value=money(overdue_total),
                    formula="sum(receivable invoice outstanding where due_on < today)",
                    source_record_ids=[invoice.id for invoice in overdue],
                    period_end=as_of,
                ),
                FactResult(
                    fact_type="expected_collection_amount",
                    value=money(expected_collection),
                    formula="total_receivables * configurable expected collection factor 0.85",
                    source_record_ids=[invoice.id for invoice in receivables],
                    period_end=as_of,
                    confidence_score=Decimal("0.85"),
                ),
            ],
            details={"overdue_invoices": days_overdue},
        )


import time
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.ai.tools.finance_tools import DraftEmailInput
from app.models.finance import Action
from app.repositories.finance import FinanceRepository, WorkflowRepository


class ReceivablesWorkflow:
    def __init__(self, db: Session):
        self.db = db
        self.finance_repo = FinanceRepository(db)
        self.workflow_repo = WorkflowRepository(db)

    def run(self, organization_id: str) -> dict:
        start = time.perf_counter()
        run = self.workflow_repo.start(organization_id, "receivables_workflow", {})
        invoices = [invoice for invoice in self.finance_repo.invoices(organization_id) if invoice.direction == "receivable" and invoice.status != "paid"]
        overdue = sorted([invoice for invoice in invoices if invoice.due_on < date.today()], key=lambda item: item.due_on)
        self.workflow_repo.step(run.id, "detect_overdue", {}, {"overdue_count": len(overdue)})
        actions = []
        for invoice in overdue[:3]:
            amount = Decimal(str(invoice.amount)) - Decimal(str(invoice.paid_amount))
            days = (date.today() - invoice.due_on).days
            action = Action(
                organization_id=organization_id,
                action_type="email_draft",
                status="draft",
                title=f"Follow up on {invoice.invoice_number}",
                payload={
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "amount": str(amount),
                    "days_overdue": days,
                    "body": f"Checking in on invoice {invoice.invoice_number} for ₹{amount:,.0f}, now {days} days overdue.",
                },
                approval_required=True,
            )
            self.db.add(action)
            actions.append(action)
        self.db.flush()
        self.workflow_repo.step(run.id, "draft_followup", {}, {"action_ids": [action.id for action in actions]})
        self.workflow_repo.finish(run, {"action_ids": [action.id for action in actions]}, duration_ms=int((time.perf_counter() - start) * 1000))
        self.db.commit()
        return {"workflow_run_id": run.id, "action_ids": [action.id for action in actions]}


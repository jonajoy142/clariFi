from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.engines.burn import BurnEngine
from app.engines.cash import CashEngine
from app.engines.forecast import ForecastEngine
from app.engines.payables import PayablesEngine
from app.engines.receivables import ReceivablesEngine
from app.engines.runway import RunwayEngine
from app.engines.tax_reserve import TaxReserveEngine
from app.engines.vendor_waste import VendorWasteEngine
from app.models.finance import AuditEventType, AuditLog, FinancialFact, Organization
from app.repositories.finance import AuditRepository, FinanceRepository, OrganizationRepository


class FinancialFactService:
    def __init__(self, db: Session):
        self.db = db
        self.finance_repo = FinanceRepository(db)
        self.audit_repo = AuditRepository(db)
        self.org_repo = OrganizationRepository(db)

    def calculate_and_persist(self, organization_id: str) -> list[FinancialFact]:
        org = self.org_repo.get(organization_id)
        if org is None:
            raise ValueError("Organization not found")

        accounts = list(self.finance_repo.accounts(organization_id))
        transactions = list(self.finance_repo.transactions(organization_id))
        invoices = list(self.finance_repo.invoices(organization_id))
        vendors = list(self.finance_repo.vendors(organization_id))
        subscriptions = list(self.finance_repo.subscriptions(organization_id))
        payroll = list(self.finance_repo.payroll(organization_id))
        today = date.today()

        outputs = [
            CashEngine().calculate(accounts, transactions, today),
            BurnEngine().calculate(transactions, payroll, today),
            ReceivablesEngine().calculate(invoices, today),
            PayablesEngine().calculate(invoices, today),
            VendorWasteEngine().calculate(vendors, subscriptions, transactions, today),
        ]

        fact_lookup: dict[str, Decimal] = {}
        source_lookup: dict[str, list[str]] = {}
        for output in outputs:
            for fact in output.facts:
                fact_lookup[fact.fact_type] = fact.value
                source_lookup[fact.fact_type] = fact.source_record_ids

        current_cash = fact_lookup.get("current_cash", Decimal("0"))
        monthly_burn = fact_lookup.get("monthly_burn", Decimal("0"))
        outputs.append(RunwayEngine().calculate(current_cash, monthly_burn, source_lookup.get("current_cash", []) + source_lookup.get("monthly_burn", [])))

        expected_inflows = fact_lookup.get("expected_collection_amount", Decimal("0"))
        expected_outflows = fact_lookup.get("upcoming_payables_30d", Decimal("0"))
        outputs.append(ForecastEngine().calculate(current_cash, monthly_burn, expected_inflows, expected_outflows, today))

        if org.user_type == "freelancer":
            reserve_percentage = Decimal(str(org.settings.get("tax_reserve_percentage", "0.25"))) if org.settings else Decimal("0.25")
            outputs.append(TaxReserveEngine().calculate(transactions, reserve_percentage, today))

        persisted: list[FinancialFact] = []
        for output in outputs:
            audit = self._audit_engine_output(organization_id, output)
            for result in output.facts:
                persisted.append(
                    FinancialFact(
                        organization_id=organization_id,
                        fact_type=result.fact_type,
                        value=result.value,
                        currency=result.currency,
                        period_start=result.period_start,
                        period_end=result.period_end,
                        formula=result.formula,
                        source_record_ids=result.source_record_ids,
                        engine_name=output.engine_name,
                        engine_version=output.engine_version,
                        confidence_score=result.confidence_score,
                        audit_log_id=audit.id,
                    )
                )

        self.finance_repo.replace_facts(organization_id, persisted)
        return persisted

    def _audit_engine_output(self, organization_id: str, output) -> AuditLog:
        return self.audit_repo.create(
            organization_id=organization_id,
            event_type=AuditEventType.calculation.value,
            actor_type="system",
            entity_type="engine",
            action=f"{output.engine_name}.calculate",
            inputs={"engine_version": output.engine_version},
            outputs={
                "facts": [
                    {
                        "fact_type": fact.fact_type,
                        "value": str(fact.value),
                        "formula": fact.formula,
                        "source_record_ids": fact.source_record_ids,
                    }
                    for fact in output.facts
                ],
                "details": output.details,
            },
            verification_status="verified",
        )


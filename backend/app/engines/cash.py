from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.engines.base import EngineOutput, FactResult, money


class CashEngine:
    name = "CashEngine"
    version = "1.0.0"

    def calculate(self, accounts: list, transactions: list, as_of: date | None = None) -> EngineOutput:
        as_of = as_of or date.today()
        current_cash = sum((money(account.current_balance) for account in accounts), Decimal("0.00"))
        by_account = {
            account.account_name: float(money(account.current_balance))
            for account in accounts
        }
        start = as_of - timedelta(days=30)
        movement_records = [txn for txn in transactions if start <= txn.occurred_on <= as_of]
        net_movement = sum((money(txn.amount) for txn in movement_records), Decimal("0.00"))

        return EngineOutput(
            engine_name=self.name,
            engine_version=self.version,
            facts=[
                FactResult(
                    fact_type="current_cash",
                    value=money(current_cash),
                    formula="sum(bank_accounts.current_balance)",
                    source_record_ids=[account.id for account in accounts],
                    period_end=as_of,
                ),
                FactResult(
                    fact_type="net_cash_movement_30d",
                    value=money(net_movement),
                    formula="sum(transactions.amount where occurred_on in trailing 30 days)",
                    source_record_ids=[txn.id for txn in movement_records],
                    period_start=start,
                    period_end=as_of,
                ),
            ],
            details={"cash_by_account": by_account},
        )


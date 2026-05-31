from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from app.engines.burn import BurnEngine
from app.engines.hiring_scenario import HiringScenarioEngine
from app.engines.receivables import ReceivablesEngine
from app.engines.runway import RunwayEngine
from app.engines.tax_reserve import TaxReserveEngine


def test_runway_calculation():
    result = RunwayEngine().calculate(Decimal("2300000"), Decimal("210000"), ["cash", "burn"])
    assert result.facts[0].value == Decimal("10.95")
    assert result.facts[0].formula == "current_cash / monthly_net_burn"


def test_burn_calculation_includes_payroll():
    today = date.today()
    transactions = [
        SimpleNamespace(id="t1", amount=Decimal("-69000"), occurred_on=today - timedelta(days=2), category="cloud"),
        SimpleNamespace(id="t2", amount=Decimal("-18000"), occurred_on=today - timedelta(days=5), category="software"),
    ]
    payroll = [SimpleNamespace(id="p1", monthly_cost=Decimal("123000"), active=True)]
    result = BurnEngine().calculate(transactions, payroll, today)
    facts = {fact.fact_type: fact.value for fact in result.facts}
    assert facts["monthly_burn"] == Decimal("210000.00")


def test_receivables_calculation_detects_overdue():
    today = date.today()
    invoices = [
        SimpleNamespace(id="i1", direction="receivable", status="overdue", amount=Decimal("42000"), paid_amount=Decimal("0"), due_on=today - timedelta(days=18), invoice_number="INV-1"),
        SimpleNamespace(id="i2", direction="receivable", status="sent", amount=Decimal("50000"), paid_amount=Decimal("0"), due_on=today + timedelta(days=5), invoice_number="INV-2"),
    ]
    result = ReceivablesEngine().calculate(invoices, today)
    facts = {fact.fact_type: fact.value for fact in result.facts}
    assert facts["total_receivables"] == Decimal("92000.00")
    assert facts["overdue_receivables"] == Decimal("42000.00")
    assert result.details["overdue_invoices"]["INV-1"] == 18


def test_hiring_scenario_changes_runway():
    result = HiringScenarioEngine().calculate(Decimal("2300000"), Decimal("210000"), Decimal("180000"))
    assert result["runway_before"] == Decimal("10.95")
    assert result["runway_after"] == Decimal("5.90")
    assert result["risk_level"] == "critical"


def test_tax_reserve_uses_configurable_percentage():
    today = date.today()
    transactions = [
        SimpleNamespace(id="t1", amount=Decimal("125000"), occurred_on=today, category="stripe_revenue"),
        SimpleNamespace(id="t2", amount=Decimal("-1000"), occurred_on=today, category="software"),
    ]
    result = TaxReserveEngine().calculate(transactions, Decimal("0.25"), today)
    facts = {fact.fact_type: fact.value for fact in result.facts}
    assert facts["suggested_tax_reserve"] == Decimal("31250.00")


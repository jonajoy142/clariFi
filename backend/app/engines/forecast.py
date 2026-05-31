from datetime import date, timedelta
from decimal import Decimal

from app.engines.base import EngineOutput, FactResult, money


class ForecastEngine:
    name = "ForecastEngine"
    version = "1.0.0"

    def calculate(self, current_cash: Decimal, monthly_burn: Decimal, expected_inflows: Decimal, expected_outflows: Decimal, as_of: date | None = None) -> EngineOutput:
        as_of = as_of or date.today()
        daily_burn = money(monthly_burn) / Decimal("30")
        facts: list[FactResult] = []
        details: dict[str, float] = {}
        for days in (30, 60, 90):
            projected = money(current_cash) + money(expected_inflows) - money(expected_outflows) - money(daily_burn * Decimal(days))
            fact_type = f"projected_cash_{days}d"
            details[fact_type] = float(projected)
            facts.append(
                FactResult(
                    fact_type=fact_type,
                    value=money(projected),
                    formula=f"current_cash + expected_inflows - expected_outflows - (monthly_burn / 30 * {days})",
                    source_record_ids=[],
                    period_start=as_of,
                    period_end=as_of + timedelta(days=days),
                    confidence_score=Decimal("0.8"),
                )
            )
        return EngineOutput(engine_name=self.name, engine_version=self.version, facts=facts, details=details)

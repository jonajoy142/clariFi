from decimal import Decimal

from app.engines.base import EngineOutput, FactResult, money


class RunwayEngine:
    name = "RunwayEngine"
    version = "1.0.0"

    def calculate(self, current_cash: Decimal, monthly_net_burn: Decimal, source_record_ids: list[str]) -> EngineOutput:
        burn = money(monthly_net_burn)
        cash = money(current_cash)
        runway = Decimal("999.00") if burn <= 0 else (cash / burn).quantize(Decimal("0.01"))
        return EngineOutput(
            engine_name=self.name,
            engine_version=self.version,
            facts=[
                FactResult(
                    fact_type="runway_months",
                    value=runway,
                    formula="current_cash / monthly_net_burn",
                    source_record_ids=source_record_ids,
                )
            ],
            details={"current_cash": float(cash), "monthly_net_burn": float(burn)},
        )

    def scenario(self, current_cash: Decimal, monthly_net_burn: Decimal, burn_delta: Decimal) -> dict:
        before_burn = money(monthly_net_burn)
        after_burn = money(before_burn + burn_delta)
        before_runway = Decimal("999.00") if before_burn <= 0 else (money(current_cash) / before_burn).quantize(Decimal("0.01"))
        after_runway = Decimal("999.00") if after_burn <= 0 else (money(current_cash) / after_burn).quantize(Decimal("0.01"))
        return {
            "runway_before": before_runway,
            "runway_after": after_runway,
            "burn_before": before_burn,
            "burn_after": after_burn,
        }


from decimal import Decimal

from app.engines.base import money
from app.engines.runway import RunwayEngine


class HiringScenarioEngine:
    name = "HiringScenarioEngine"
    version = "1.0.0"

    def calculate(self, current_cash: Decimal, monthly_burn: Decimal, new_monthly_payroll: Decimal) -> dict:
        scenario = RunwayEngine().scenario(current_cash, monthly_burn, money(new_monthly_payroll))
        runway_after = scenario["runway_after"]
        risk_level = "critical" if runway_after < Decimal("6") else "elevated" if runway_after < Decimal("9") else "manageable"
        return {
            **scenario,
            "payroll_increase": money(new_monthly_payroll),
            "risk_level": risk_level,
            "formula": "scenario_runway = current_cash / (monthly_burn + new_monthly_payroll)",
            "engine_name": self.name,
            "engine_version": self.version,
        }


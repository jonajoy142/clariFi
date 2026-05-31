from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class FactResult:
    fact_type: str
    value: Decimal
    formula: str
    source_record_ids: list[str]
    period_start: date | None = None
    period_end: date | None = None
    currency: str = "INR"
    confidence_score: Decimal = Decimal("1.0")


@dataclass(frozen=True)
class EngineOutput:
    engine_name: str
    engine_version: str
    facts: list[FactResult] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


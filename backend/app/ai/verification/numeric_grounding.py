import re
from decimal import Decimal, InvalidOperation

from app.ai.schemas.outputs import FinancialContextPack, VerificationResult

NUMBER_RE = re.compile(r"(?<![A-Za-z])(?:₹\s*)?(\d[\d,]*(?:\.\d+)?)(?:\s*(?:months?|days?|%|percent))?", re.IGNORECASE)


def extract_numbers(text: str) -> list[Decimal]:
    numbers: list[Decimal] = []
    for match in NUMBER_RE.finditer(text):
        raw = match.group(1).replace(",", "")
        try:
            numbers.append(Decimal(raw).quantize(Decimal("0.01")))
        except InvalidOperation:
            continue
    return numbers


def verify_numeric_grounding(text: str, context: FinancialContextPack) -> VerificationResult:
    allowed = {_normalize(number) for number in context.allowed_numbers}
    allowed.update({_normalize(Decimal(str(common))) for common in [0, 1, 2, 3, 5, 7, 18, 30, 60, 90, 100]})
    unsupported: list[str] = []
    for number in extract_numbers(text):
        normalized = _normalize(number)
        if normalized not in allowed:
            unsupported.append(str(number))
    if unsupported:
        return VerificationResult(
            passed=False,
            reason="AI response contains numeric values that are not present in the verified FinancialContextPack.",
            unsupported_numbers=unsupported,
        )
    return VerificationResult(passed=True, reason="All numeric claims are grounded in verified facts or approved tool inputs.")


def _normalize(value: Decimal) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("0.00")


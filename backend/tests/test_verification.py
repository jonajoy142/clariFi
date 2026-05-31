from decimal import Decimal

from app.ai.schemas.outputs import FinancialContextPack
from app.ai.verification.numeric_grounding import verify_numeric_grounding


def test_numeric_grounding_accepts_allowed_numbers():
    context = FinancialContextPack(
        organization_id="org",
        user_type="startup",
        allowed_numbers=[Decimal("2300000"), Decimal("210000"), Decimal("10.95")],
    )
    result = verify_numeric_grounding("Cash is ₹2,300,000, burn is ₹210,000, runway is 10.95 months.", context)
    assert result.passed


def test_numeric_grounding_rejects_unsupported_numbers():
    context = FinancialContextPack(
        organization_id="org",
        user_type="startup",
        allowed_numbers=[Decimal("2300000")],
    )
    result = verify_numeric_grounding("Cash is ₹2,300,000 and mystery savings are ₹999,999.", context)
    assert not result.passed
    assert "999999.00" in result.unsupported_numbers


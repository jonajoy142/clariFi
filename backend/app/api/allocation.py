# ── allocation.py ─────────────────────────────────────────────────────────
from fastapi import APIRouter
from app.models.profile import UserFinancialProfile
from app.engines.loan_allocation_engine import calculate_monthly_allocation

router = APIRouter()

@router.post("/monthly")
def monthly_allocation(profile: UserFinancialProfile):
    return calculate_monthly_allocation(profile)

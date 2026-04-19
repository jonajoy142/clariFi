# ── tax.py ───────────────────────────────────────────────────────────────────
from fastapi import APIRouter
from app.models.profile import UserFinancialProfile
from app.engines.tax_engine import run_intelligent_tax_analysis

router = APIRouter()

@router.post("/analyse")
def analyse_tax(profile: UserFinancialProfile):
    return run_intelligent_tax_analysis(profile)

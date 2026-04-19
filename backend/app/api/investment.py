from fastapi import APIRouter
from app.models.profile import UserFinancialProfile
from app.engines.investment_engine import run_investment_analysis

router = APIRouter()

@router.post("/analyse")
def analyse_investment(profile: UserFinancialProfile):
    return run_investment_analysis(profile)

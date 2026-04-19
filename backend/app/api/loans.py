from fastapi import APIRouter
from app.models.profile import UserFinancialProfile
from app.engines.loan_allocation_engine import run_loan_analysis

router = APIRouter()

@router.post("/analyse")
def analyse_loans(profile: UserFinancialProfile):
    return run_loan_analysis(profile)

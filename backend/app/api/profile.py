# app/api/profile.py
from fastapi import APIRouter
from app.models.profile import UserFinancialProfile

router = APIRouter()
# In-memory store for demo (no DB needed for portfolio)
_profiles: dict = {}

@router.post("/save")
def save_profile(profile: UserFinancialProfile, session_id: str = "demo"):
    _profiles[session_id] = profile
    return {"status": "saved", "session_id": session_id}

@router.get("/get")
def get_profile(session_id: str = "demo"):
    profile = _profiles.get(session_id)
    if not profile:
        return {"status": "not_found"}
    return profile

@router.get("/demo")
def get_demo_profile():
    """Returns a pre-filled demo profile for portfolio showcase"""
    from app.models.profile import (UserFinancialProfile, SalaryIncome, City,
        Investments, Loans, Loan, Assets, OtherIncome, Goal, EmploymentType)
    return UserFinancialProfile(
        age=28,
        employment_type=EmploymentType.salaried,
        salary=SalaryIncome(
            gross_annual=1800000,
            basic_salary_annual=720000,
            hra_received_annual=360000,
            rent_paid_monthly=25000,
            city=City.metro,
            epf_employee_annual=86400
        ),
        other_income=OtherIncome(fd_interest_annual=12000),
        investments=Investments(
            elss_annual=50000,
            ppf_annual=50000,
            nps_tier1_annual=50000,
            life_insurance_premium_annual=24000,
            health_insurance_self_annual=15000,
            health_insurance_parents_annual=20000,
            parents_senior_citizen=True,
            existing_sip_monthly=15000,
            mutual_fund_corpus=450000,
            stocks_value=120000
        ),
        loans=Loans(
            home_loan=Loan(name="Home Loan", outstanding=4500000,
                           emi_monthly=38000, rate_annual=8.5, tenure_remaining_months=240),
            home_loan_interest_annual=380000
        ),
        assets=Assets(
            bank_balance=180000,
            gold_grams=50,
            epf_balance=320000,
            ppf_balance=180000,
            fd_value=200000
        ),
        monthly_expenses=45000,
        goals=[
            Goal(name="Child Education", target_amount=5000000, target_years=15),
            Goal(name="Retirement", target_amount=30000000, target_years=32),
        ],
        risk_appetite="moderate",
        additional_context="Recently got promoted, salary increased from ₹14L to ₹18L. Confused about old vs new regime."
    )

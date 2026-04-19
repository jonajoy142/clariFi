from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class City(str, Enum):
    metro = "metro"       # Mumbai, Delhi, Kolkata, Chennai
    non_metro = "non_metro"

class EmploymentType(str, Enum):
    salaried = "salaried"
    freelancer = "freelancer"
    business = "business"
    both = "both"         # salaried + freelance

# ---------- Income ----------
class SalaryIncome(BaseModel):
    gross_annual: float = Field(..., description="Annual CTC in INR")
    basic_salary_annual: float = Field(..., description="Basic salary annual — used for HRA, EPF")
    hra_received_annual: float = Field(0, description="HRA received annually from employer")
    rent_paid_monthly: float = Field(0, description="Actual rent paid per month")
    city: City = City.metro
    epf_employee_annual: float = Field(0, description="EPF contribution by employee annually")

class FreelanceIncome(BaseModel):
    annual_inr: float = Field(0, description="Total freelance income in INR annually")
    usd_monthly: float = Field(0, description="USD income monthly — converted at live rate")
    eur_monthly: float = Field(0, description="EUR income monthly")
    gst_registered: bool = False

class OtherIncome(BaseModel):
    rental_annual: float = Field(0, description="Rental income from property annually")
    fd_interest_annual: float = Field(0, description="FD / savings interest annually")
    dividend_annual: float = Field(0, description="Dividend income annually")
    capital_gains_stcg: float = Field(0, description="Short-term capital gains")
    capital_gains_ltcg: float = Field(0, description="Long-term capital gains above ₹1L")

# ---------- Investments ----------
class Investments(BaseModel):
    elss_annual: float = Field(0, description="ELSS mutual fund investment annually")
    ppf_annual: float = Field(0, description="PPF contribution annually")
    nps_tier1_annual: float = Field(0, description="NPS Tier 1 contribution annually")
    life_insurance_premium_annual: float = Field(0, description="Life insurance premiums annually")
    ulip_annual: float = Field(0, description="ULIP premium annually")
    home_loan_principal_annual: float = Field(0, description="Home loan principal repaid annually")
    sukanya_samriddhi_annual: float = Field(0, description="Sukanya Samriddhi Yojana annual")
    tuition_fees_annual: float = Field(0, description="Children tuition fees annual")
    # Health
    health_insurance_self_annual: float = Field(0, description="Health insurance for self/family")
    health_insurance_parents_annual: float = Field(0, description="Health insurance for parents")
    parents_senior_citizen: bool = Field(False, description="Are parents senior citizens (60+)?")
    # SIPs (for projection, not tax)
    existing_sip_monthly: float = Field(0, description="Current monthly SIP amount")
    mutual_fund_corpus: float = Field(0, description="Current MF corpus value")
    stocks_value: float = Field(0, description="Current direct stocks value")

# ---------- Loans ----------
class Loan(BaseModel):
    name: str
    outstanding: float
    emi_monthly: float
    rate_annual: float  # interest rate %
    tenure_remaining_months: int

class Loans(BaseModel):
    home_loan: Optional[Loan] = None
    home_loan_interest_annual: float = Field(0, description="Interest component paid this year — for Sec 24B")
    car_loan: Optional[Loan] = None
    personal_loan: Optional[Loan] = None
    education_loan: Optional[Loan] = None
    credit_card_due: float = Field(0, description="Outstanding credit card dues")

# ---------- Assets ----------
class Assets(BaseModel):
    bank_balance: float = Field(0)
    gold_grams: float = Field(0)
    real_estate_value: float = Field(0, description="Self-assessed property value")
    fd_value: float = Field(0)
    ppf_balance: float = Field(0)
    nps_balance: float = Field(0)
    epf_balance: float = Field(0)
    other_assets: float = Field(0)

# ---------- Goals ----------
class Goal(BaseModel):
    name: str
    target_amount: float
    target_years: int

# ---------- Master Profile ----------
class UserFinancialProfile(BaseModel):
    # Personal
    age: int = Field(..., ge=18, le=80)
    employment_type: EmploymentType = EmploymentType.salaried
    financial_year: str = Field("2025-26", description="FY for tax calculations")

    # Income
    salary: Optional[SalaryIncome] = None
    freelance: Optional[FreelanceIncome] = None
    other_income: OtherIncome = OtherIncome()

    # Financial data
    investments: Investments = Investments()
    loans: Loans = Loans()
    assets: Assets = Assets()

    # Goals
    monthly_expenses: float = Field(0, description="Average monthly living expenses")
    goals: List[Goal] = []

    # Context for AI reasoning
    risk_appetite: str = Field("moderate", description="conservative / moderate / aggressive")
    additional_context: str = Field("", description="Any extra info user wants AI to know")

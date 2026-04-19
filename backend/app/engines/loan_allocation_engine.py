"""
Loan Engine — Amortisation, prepayment analysis, debt prioritisation.
Allocation Engine — Monthly surplus split with AI reasoning.
"""
from app.models.profile import UserFinancialProfile, Loan
from app.core.config import settings
import anthropic, json, math

# ── LOAN ENGINE ──────────────────────────────────────────────────────────────

def amortisation_schedule(outstanding: float, rate_annual: float,
                           emi: float, months: int) -> dict:
    r = rate_annual / 12 / 100
    schedule = []
    balance = outstanding
    total_interest = 0
    for m in range(1, min(months + 1, 13)):  # Show first 12 months
        interest = balance * r
        principal = emi - interest
        balance = max(0, balance - principal)
        total_interest += interest
        schedule.append({
            "month": m,
            "emi": round(emi, 0),
            "principal": round(principal, 0),
            "interest": round(interest, 0),
            "balance": round(balance, 0)
        })
    total_interest_full = outstanding * r * months - outstanding * ((1+r)**months - 1 - r*months) / ((1+r)**months - 1)
    return {
        "outstanding": outstanding,
        "rate_annual": rate_annual,
        "emi": emi,
        "tenure_months": months,
        "first_12_months": schedule,
        "total_interest_payable": round(abs(total_interest_full), 0),
        "total_payment": round(emi * months, 0)
    }

def prepayment_impact(outstanding: float, rate_annual: float,
                       emi: float, tenure_months: int, prepay_amount: float) -> dict:
    r = rate_annual / 12 / 100

    def months_to_payoff(bal, r, emi):
        if emi <= bal * r:
            return float('inf')
        return math.ceil(math.log(emi / (emi - bal * r)) / math.log(1 + r))

    original_months = tenure_months
    original_interest = emi * original_months - outstanding

    new_outstanding = outstanding - prepay_amount
    new_months = months_to_payoff(new_outstanding, r, emi)
    new_interest = emi * new_months - new_outstanding

    months_saved = original_months - new_months
    interest_saved = original_interest - new_interest

    return {
        "prepay_amount": prepay_amount,
        "original_tenure_months": original_months,
        "new_tenure_months": int(new_months),
        "months_saved": int(months_saved),
        "years_saved": round(months_saved / 12, 1),
        "interest_saved": round(interest_saved, 0),
        "working": f"Prepay ₹{prepay_amount:,.0f} → tenure reduces by {int(months_saved)} months, saves ₹{interest_saved:,.0f} in interest"
    }

def debt_avalanche_order(loans_data: dict) -> list:
    """Sort loans by interest rate — highest first (avalanche method)"""
    loan_list = []
    if loans_data.home_loan:
        l = loans_data.home_loan
        loan_list.append({"name": "Home Loan", "rate": l.rate_annual, "outstanding": l.outstanding, "emi": l.emi_monthly})
    if loans_data.car_loan:
        l = loans_data.car_loan
        loan_list.append({"name": "Car Loan", "rate": l.rate_annual, "outstanding": l.outstanding, "emi": l.emi_monthly})
    if loans_data.personal_loan:
        l = loans_data.personal_loan
        loan_list.append({"name": "Personal Loan", "rate": l.rate_annual, "outstanding": l.outstanding, "emi": l.emi_monthly})
    if loans_data.education_loan:
        l = loans_data.education_loan
        loan_list.append({"name": "Education Loan", "rate": l.rate_annual, "outstanding": l.outstanding, "emi": l.emi_monthly})
    if loans_data.credit_card_due > 0:
        loan_list.append({"name": "Credit Card", "rate": 36, "outstanding": loans_data.credit_card_due, "emi": 0})
    return sorted(loan_list, key=lambda x: x["rate"], reverse=True)

def run_loan_analysis(profile: UserFinancialProfile) -> dict:
    results = {}
    loans = profile.loans
    total_emi = sum([
        loans.home_loan.emi_monthly if loans.home_loan else 0,
        loans.car_loan.emi_monthly if loans.car_loan else 0,
        loans.personal_loan.emi_monthly if loans.personal_loan else 0,
        loans.education_loan.emi_monthly if loans.education_loan else 0,
    ])
    monthly_income = (profile.salary.gross_annual / 12) if profile.salary else 0
    emi_to_income = (total_emi / monthly_income * 100) if monthly_income else 0

    results["total_monthly_emi"] = total_emi
    results["emi_to_income_ratio"] = round(emi_to_income, 1)
    results["emi_health"] = "healthy" if emi_to_income < 30 else "high" if emi_to_income < 45 else "critical"
    results["debt_priority_order"] = debt_avalanche_order(loans)

    if loans.home_loan:
        l = loans.home_loan
        results["home_loan_amortisation"] = amortisation_schedule(
            l.outstanding, l.rate_annual, l.emi_monthly, l.tenure_remaining_months)
        results["home_loan_prepay_1L"] = prepayment_impact(
            l.outstanding, l.rate_annual, l.emi_monthly, l.tenure_remaining_months, 100000)

    # AI analysis
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = f"""You are a debt management expert for India. Analyse this person's loan situation.

LOAN DATA:
- Total monthly EMI: ₹{total_emi:,.0f}
- Monthly income: ₹{monthly_income:,.0f}
- EMI-to-income ratio: {emi_to_income:.1f}%
- Home loan: {f"₹{loans.home_loan.outstanding:,.0f} at {loans.home_loan.rate_annual}%" if loans.home_loan else "None"}
- Car loan: {f"₹{loans.car_loan.outstanding:,.0f} at {loans.car_loan.rate_annual}%" if loans.car_loan else "None"}
- Personal loan: {f"₹{loans.personal_loan.outstanding:,.0f} at {loans.personal_loan.rate_annual}%" if loans.personal_loan else "None"}
- Credit card dues: ₹{loans.credit_card_due:,.0f}
- Debt priority order: {results["debt_priority_order"]}

Provide specific, actionable debt management advice. Consider:
1. Is EMI burden sustainable?
2. Which loan to tackle first and why?
3. Should they prepay or invest surplus?
4. Any balance transfer or refinancing opportunity?

Respond in JSON:
{{
  "debt_health_verdict": "<one sentence assessment>",
  "priority_action": "<most important thing to do right now>",
  "recommendations": [
    {{"action": "<specific>", "reasoning": "<why>", "impact": "<INR or time saved>"}}
  ],
  "credit_card_urgent": <true/false>,
  "ai_summary": "<2 sentence debt situation summary>"
}}"""
    response = client.messages.create(model=settings.model, max_tokens=800,
        messages=[{"role": "user", "content": prompt}])
    raw = response.content[0].text.strip().replace("```json","").replace("```","").strip()
    results["ai_analysis"] = json.loads(raw)
    return results

# ── ALLOCATION ENGINE ────────────────────────────────────────────────────────

def calculate_monthly_allocation(profile: UserFinancialProfile) -> dict:
    monthly_income = 0
    if profile.salary:
        monthly_income += profile.salary.gross_annual / 12
    if profile.freelance:
        monthly_income += profile.freelance.annual_inr / 12

    total_emi = sum([
        profile.loans.home_loan.emi_monthly if profile.loans.home_loan else 0,
        profile.loans.car_loan.emi_monthly if profile.loans.car_loan else 0,
        profile.loans.personal_loan.emi_monthly if profile.loans.personal_loan else 0,
        profile.loans.education_loan.emi_monthly if profile.loans.education_loan else 0,
    ])

    existing_sip = profile.investments.existing_sip_monthly
    fixed_costs = profile.monthly_expenses + total_emi + existing_sip
    surplus = max(0, monthly_income - fixed_costs)

    # Emergency fund check
    emergency_target = profile.monthly_expenses * 6
    emergency_current = profile.assets.bank_balance
    emergency_gap = max(0, emergency_target - emergency_current)
    emergency_monthly = min(surplus * 0.3, emergency_gap / 6) if emergency_gap > 0 else 0

    # Advance tax provision (approx 30% of income above 10L)
    annual_income = monthly_income * 12
    advance_tax_monthly = max(0, (annual_income - 1000000) * 0.30 / 12) if annual_income > 1000000 else 0

    # Investable after emergency and tax provision
    investable = max(0, surplus - emergency_monthly - advance_tax_monthly)

    allocation = {
        "monthly_income": round(monthly_income, 0),
        "fixed_costs": {
            "living_expenses": profile.monthly_expenses,
            "total_emi": total_emi,
            "existing_sip": existing_sip,
            "total": round(fixed_costs, 0)
        },
        "surplus": round(surplus, 0),
        "allocation_plan": {
            "emergency_fund_topup": round(emergency_monthly, 0),
            "advance_tax_provision": round(advance_tax_monthly, 0),
            "investable_surplus": round(investable, 0),
        },
        "emergency_fund": {
            "target": round(emergency_target, 0),
            "current": emergency_current,
            "gap": round(emergency_gap, 0),
            "months_covered": round(emergency_current / profile.monthly_expenses, 1) if profile.monthly_expenses else 0
        },
        "working": f"Income ₹{monthly_income:,.0f} − Fixed costs ₹{fixed_costs:,.0f} = Surplus ₹{surplus:,.0f}"
    }

    # AI allocation recommendation
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = f"""You are a personal finance CFO for an Indian professional. Tell them exactly how to allocate their monthly surplus.

FINANCIAL SNAPSHOT:
- Monthly income: ₹{monthly_income:,.0f}
- Monthly expenses: ₹{profile.monthly_expenses:,.0f}
- Total EMI: ₹{total_emi:,.0f}
- Current SIP: ₹{existing_sip:,.0f}
- Monthly surplus: ₹{surplus:,.0f}
- Emergency fund: ₹{emergency_current:,.0f} ({round(emergency_current/profile.monthly_expenses,1) if profile.monthly_expenses else 0} months covered)
- Emergency fund target: ₹{emergency_target:,.0f} (6 months)
- Age: {profile.age}, Risk appetite: {profile.risk_appetite}
- Goals: {[f"{g.name}: ₹{g.target_amount:,.0f} in {g.target_years}yr" for g in profile.goals]}
- Additional context: {profile.additional_context}

Give a SPECIFIC monthly allocation plan for the surplus of ₹{surplus:,.0f}.
Be precise with rupee amounts. Consider emergency fund, investments, loan prepayment, and goals.

Respond in JSON:
{{
  "surplus_available": {surplus},
  "allocation": [
    {{"bucket": "<name>", "amount": <number>, "percentage": <number>, "reasoning": "<why this amount>"}}
  ],
  "total_check": <must equal surplus>,
  "priority_insight": "<what's most important for them right now>",
  "next_month_action": "<one specific thing to do this month>",
  "ai_summary": "<2 sentence monthly CFO summary>"
}}"""
    response = client.messages.create(model=settings.model, max_tokens=1000,
        messages=[{"role": "user", "content": prompt}])
    raw = response.content[0].text.strip().replace("```json","").replace("```","").strip()
    allocation["ai_analysis"] = json.loads(raw)
    return allocation

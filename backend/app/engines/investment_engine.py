"""
Investment Engine — SIP planning, goal-based calculations, loan vs invest scenarios.
All math is pure Python. LLM provides intelligent recommendations on top.
"""
from app.models.profile import UserFinancialProfile
from app.core.config import settings
import anthropic, json, math

def calculate_sip_for_goal(target: float, years: int, annual_return: float = 0.12) -> dict:
    months = years * 12
    r = annual_return / 12
    if r == 0:
        monthly_sip = target / months
    else:
        monthly_sip = (target * r) / ((1 + r) ** months - 1)
    return {
        "target_amount": target,
        "years": years,
        "assumed_annual_return": f"{annual_return*100:.0f}%",
        "monthly_sip_required": round(monthly_sip, 0),
        "total_invested": round(monthly_sip * months, 0),
        "wealth_gained": round(target - monthly_sip * months, 0),
        "working": f"PMT formula: target ₹{target:,.0f} in {years}yr at {annual_return*100:.0f}% = ₹{monthly_sip:,.0f}/month"
    }

def project_existing_sip(monthly_sip: float, years: int, annual_return: float = 0.12) -> dict:
    months = years * 12
    r = annual_return / 12
    if r == 0:
        future_value = monthly_sip * months
    else:
        future_value = monthly_sip * (((1 + r) ** months - 1) / r) * (1 + r)
    total_invested = monthly_sip * months
    return {
        "monthly_sip": monthly_sip,
        "years": years,
        "projected_value": round(future_value, 0),
        "total_invested": round(total_invested, 0),
        "wealth_gained": round(future_value - total_invested, 0),
        "working": f"FV = ₹{monthly_sip:,.0f} × [((1+r)^{months}-1)/r] × (1+r) = ₹{future_value:,.0f}"
    }

def step_up_sip_projection(initial_sip: float, annual_stepup_pct: float,
                            years: int, annual_return: float = 0.12) -> dict:
    r = annual_return / 12
    g = annual_stepup_pct / 12
    months = years * 12
    fv = 0
    total_invested = 0
    current_sip = initial_sip
    for month in range(1, months + 1):
        if month % 12 == 1 and month > 1:
            current_sip *= (1 + annual_stepup_pct)
        fv = (fv + current_sip) * (1 + r)
        total_invested += current_sip
    return {
        "initial_monthly_sip": initial_sip,
        "annual_stepup": f"{annual_stepup_pct*100:.0f}%",
        "final_monthly_sip": round(current_sip, 0),
        "projected_value": round(fv, 0),
        "total_invested": round(total_invested, 0),
        "extra_vs_flat_sip": round(fv - project_existing_sip(initial_sip, years, annual_return)["projected_value"], 0)
    }

def loan_vs_invest(loan_outstanding: float, loan_rate: float,
                   prepay_amount: float, invest_return: float = 0.12) -> dict:
    # Interest saved by prepaying
    # Simplified: interest saved = prepay_amount * loan_rate (first year impact)
    interest_saved_yr1 = prepay_amount * loan_rate
    # Investment return if deployed instead
    invest_return_yr1 = prepay_amount * invest_return
    post_tax_invest = invest_return_yr1 * 0.90  # approx 10% tax on LTCG/interest

    better = "prepay" if interest_saved_yr1 > post_tax_invest else "invest"
    net_advantage = abs(interest_saved_yr1 - post_tax_invest)

    return {
        "prepay_amount": prepay_amount,
        "loan_rate": f"{loan_rate*100:.1f}%",
        "interest_saved_year1": round(interest_saved_yr1, 0),
        "invest_return_year1_gross": round(invest_return_yr1, 0),
        "invest_return_year1_post_tax": round(post_tax_invest, 0),
        "recommendation": better,
        "net_advantage": round(net_advantage, 0),
        "working": f"Prepay saves ₹{interest_saved_yr1:,.0f} interest. Investing returns ₹{post_tax_invest:,.0f} post-tax. {'Prepay wins' if better=='prepay' else 'Invest wins'} by ₹{net_advantage:,.0f}/yr.",
        "note": "This is year-1 analysis. For full amortisation impact, consult the detailed loan engine."
    }

def fire_number(monthly_expenses: float, annual_return: float = 0.08,
                withdrawal_rate: float = 0.04) -> dict:
    annual_expenses = monthly_expenses * 12
    corpus_needed = annual_expenses / withdrawal_rate
    return {
        "monthly_expenses": monthly_expenses,
        "annual_expenses": annual_expenses,
        "fire_corpus": corpus_needed,
        "withdrawal_rate": f"{withdrawal_rate*100:.0f}%",
        "assumed_post_fire_return": f"{annual_return*100:.0f}%",
        "working": f"FIRE corpus = Annual expenses ÷ withdrawal rate = ₹{annual_expenses:,.0f} ÷ {withdrawal_rate} = ₹{corpus_needed:,.0f}"
    }

def run_investment_analysis(profile: UserFinancialProfile) -> dict:
    results = {}

    # Existing SIP projection
    if profile.investments.existing_sip_monthly > 0:
        results["sip_10yr"] = project_existing_sip(profile.investments.existing_sip_monthly, 10)
        results["sip_20yr"] = project_existing_sip(profile.investments.existing_sip_monthly, 20)
        results["stepup_sip"] = step_up_sip_projection(
            profile.investments.existing_sip_monthly, 0.10, 20)

    # Goal-based SIP requirements
    results["goals_analysis"] = []
    for goal in profile.goals:
        sip_req = calculate_sip_for_goal(goal.target_amount, goal.target_years)
        results["goals_analysis"].append({"goal": goal.name, **sip_req})

    # FIRE
    if profile.monthly_expenses > 0:
        results["fire"] = fire_number(profile.monthly_expenses)

    # Loan vs invest (home loan)
    if profile.loans.home_loan:
        results["loan_vs_invest"] = loan_vs_invest(
            profile.loans.home_loan.outstanding,
            profile.loans.home_loan.rate_annual / 100,
            100000  # assume ₹1L available for decision
        )

    # AI layer — intelligent recommendations
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = f"""You are a senior Indian financial advisor. Analyse this person's investment situation.

PROFILE:
- Age: {profile.age}, Risk appetite: {profile.risk_appetite}
- Monthly expenses: ₹{profile.monthly_expenses:,.0f}
- Existing monthly SIP: ₹{profile.investments.existing_sip_monthly:,.0f}
- MF corpus: ₹{profile.investments.mutual_fund_corpus:,.0f}
- Stocks value: ₹{profile.investments.stocks_value:,.0f}
- EPF balance: ₹{profile.assets.epf_balance:,.0f}
- PPF balance: ₹{profile.assets.ppf_balance:,.0f}
- NPS balance: ₹{profile.assets.nps_balance:,.0f}

CALCULATED RESULTS:
{json.dumps(results, indent=2, default=str)}

GOALS: {[f"{g.name}: ₹{g.target_amount:,.0f} in {g.target_years}yr" for g in profile.goals]}

Provide intelligent investment advice. Consider:
1. Is their asset allocation right for their age and risk appetite?
2. Are they on track for their goals?
3. ELSS vs PPF vs NPS — what mix makes sense for them specifically?
4. What should they prioritise — SIP increase, lumpsum, loan prepay?
5. Any gaps in their investment strategy?

Respond in JSON:
{{
  "portfolio_health": "good/fair/needs_attention",
  "key_insight": "<one powerful observation about their portfolio>",
  "asset_allocation_verdict": "<are they well diversified for their age?>",
  "top_recommendations": [
    {{"priority": 1, "action": "<specific action>", "reasoning": "<why>", "impact": "<expected impact>"}}
  ],
  "goals_on_track": [{{"goal": "<name>", "status": "on_track/behind/ahead", "note": "<specific advice>"}}],
  "ai_summary": "<2-3 sentence overall investment health summary>"
}}"""

    response = client.messages.create(
        model=settings.model, max_tokens=1200,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip().replace("```json","").replace("```","").strip()
    results["ai_analysis"] = json.loads(raw)
    results["verified"] = True
    return results

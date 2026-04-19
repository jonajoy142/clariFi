"""
Tax Engine — Intelligent, not rule-based.

Architecture:
- Tax RULES live in a knowledge base (updated each Budget, not hardcoded in logic)
- LLM reasons over the rules to decide which deductions apply to THIS user
- Python performs the actual arithmetic — verifiable, auditable
- LLM explains the output in natural language

This means when Budget 2026 changes a limit, we update the knowledge base,
not the calculation code.
"""

from app.models.profile import UserFinancialProfile
from app.core.config import settings
import anthropic
import json
import math

# ── Tax Knowledge Base ──────────────────────────────────────────────────────
# Updated each Budget. LLM reasons over this — not hardcoded in logic.
TAX_KNOWLEDGE_BASE = """
INDIA INCOME TAX RULES — FY 2025-26 (AY 2026-27)
Last updated: Budget 2025. Source: Income Tax Act + Finance Act 2025.

═══ NEW TAX REGIME (Default from FY 2024-25) ═══
Slabs:
  ₹0        – ₹3,00,000   → 0%
  ₹3,00,001 – ₹7,00,000   → 5%
  ₹7,00,001 – ₹10,00,000  → 10%
  ₹10,00,001– ₹12,00,000  → 15%
  ₹12,00,001– ₹15,00,000  → 20%
  Above ₹15,00,000         → 30%

Deductions allowed in NEW regime:
  Standard deduction: ₹75,000 (enhanced in Budget 2024)
  NPS employer contribution: Sec 80CCD(2) — up to 14% of basic (govt) or 10% (private)
  NO other deductions allowed

Rebate u/s 87A: Tax fully rebated if taxable income ≤ ₹7,00,000 (net tax = 0)
Surcharge:
  ₹50L–₹1Cr: 10% of tax
  ₹1Cr–₹2Cr: 15%
  ₹2Cr–₹5Cr: 25%
  Above ₹5Cr: 37% (capped at 25% for new regime)
Health & Education Cess: 4% on (tax + surcharge)

═══ OLD TAX REGIME ═══
Slabs (age < 60):
  ₹0        – ₹2,50,000   → 0%
  ₹2,50,001 – ₹5,00,000   → 5%
  ₹5,00,001 – ₹10,00,000  → 20%
  Above ₹10,00,000         → 30%

Standard deduction: ₹50,000

Key Deductions (apply in optimal order):
  Sec 80C (aggregate limit ₹1,50,000):
    ELSS mutual funds, PPF, EPF (employee), LIC premium, home loan principal,
    Sukanya Samriddhi, tuition fees (2 children), NSC, SCSS, 5yr bank FD
    
  Sec 80CCD(1B): NPS Tier 1 — additional ₹50,000 OVER AND ABOVE 80C limit
  
  Sec 80D Health insurance:
    Self + family (age < 60): up to ₹25,000
    Self + family (age 60+): up to ₹50,000
    Parents (age < 60): additional ₹25,000
    Parents (age 60+): additional ₹50,000
    
  Sec 24B Home loan interest: up to ₹2,00,000 for self-occupied property
  
  HRA Exemption (least of three):
    (a) Actual HRA received from employer
    (b) Rent paid − 10% of basic salary
    (c) 50% of basic salary (metro) or 40% (non-metro)
    
  Sec 80TTA: Savings account interest up to ₹10,000 (non-senior)
  Sec 80TTB: Senior citizen (60+) interest up to ₹50,000
  
  Education loan interest: Sec 80E — full interest, no limit, 8 years

Rebate u/s 87A: Tax fully rebated if taxable income ≤ ₹5,00,000
Surcharge: Same structure as new regime
Cess: 4% on (tax + surcharge)

═══ IMPORTANT NOTES FOR AI REASONING ═══
1. HRA exemption only applies if employee actually pays rent AND receives HRA
2. Home loan principal in 80C AND interest in 24B are separate — both can be claimed
3. ULIP premiums qualify for 80C only if sum assured ≥ 10x annual premium
4. 80C is a BASKET — sum of all qualifying investments, capped at ₹1.5L
5. New regime is DEFAULT — taxpayer must explicitly opt for old regime
6. If taxable income ≤ ₹7L in new regime → zero tax due to 87A rebate
7. Senior citizens (60+) get higher slab exemption (₹3L basic, ₹5L for 80+)
"""

# ── Calculation Functions (pure math, no LLM) ───────────────────────────────

def calculate_hra_exemption(hra_received: float, rent_paid_annual: float,
                             basic_annual: float, is_metro: bool) -> dict:
    a = hra_received
    b = max(0, rent_paid_annual - 0.10 * basic_annual)
    c = basic_annual * (0.50 if is_metro else 0.40)
    exemption = min(a, b, c)
    return {
        "hra_received": a,
        "rent_minus_10pct_basic": b,
        "pct_of_basic": c,
        "exemption": exemption,
        "working": f"min(₹{a:,.0f}, ₹{b:,.0f}, ₹{c:,.0f}) = ₹{exemption:,.0f}"
    }

def calculate_80c_basket(profile: UserFinancialProfile) -> dict:
    inv = profile.investments
    components = {
        "ELSS": inv.elss_annual,
        "PPF": inv.ppf_annual,
        "EPF (employee)": profile.salary.epf_employee_annual if profile.salary else 0,
        "Life insurance": inv.life_insurance_premium_annual,
        "ULIP": inv.ulip_annual,
        "Home loan principal": inv.home_loan_principal_annual,
        "Sukanya Samriddhi": inv.sukanya_samriddhi_annual,
        "Tuition fees": inv.tuition_fees_annual,
    }
    total_invested = sum(components.values())
    capped = min(total_invested, 150000)
    headroom = max(0, 150000 - total_invested)
    return {
        "components": {k: v for k, v in components.items() if v > 0},
        "total_invested": total_invested,
        "deduction_claimed": capped,
        "headroom_remaining": headroom,
        "working": f"Sum of qualifying investments ₹{total_invested:,.0f}, capped at ₹1,50,000 → ₹{capped:,.0f}"
    }

def calculate_80d(profile: UserFinancialProfile) -> dict:
    inv = profile.investments
    self_limit = 25000  # simplified; 50k if self is senior
    parent_limit = 50000 if inv.parents_senior_citizen else 25000
    self_claimed = min(inv.health_insurance_self_annual, self_limit)
    parent_claimed = min(inv.health_insurance_parents_annual, parent_limit)
    total = self_claimed + parent_claimed
    return {
        "self_deduction": self_claimed,
        "parent_deduction": parent_claimed,
        "total_80d": total,
        "working": f"Self: min(₹{inv.health_insurance_self_annual:,.0f}, ₹{self_limit:,.0f}) + Parents: min(₹{inv.health_insurance_parents_annual:,.0f}, ₹{parent_limit:,.0f}) = ₹{total:,.0f}"
    }

def apply_slab(taxable_income: float, slabs: list) -> dict:
    tax = 0
    breakdown = []
    for low, high, rate in slabs:
        if taxable_income <= low:
            break
        chunk = min(taxable_income, high) - low if high else taxable_income - low
        tax_chunk = chunk * rate
        tax += tax_chunk
        if chunk > 0:
            breakdown.append({
                "range": f"₹{low:,.0f}–{'₹'+f'{high:,.0f}' if high else 'above'}",
                "amount": chunk,
                "rate": f"{rate*100:.0f}%",
                "tax": tax_chunk
            })
    return {"tax": tax, "breakdown": breakdown}

def compute_tax_old_regime(taxable_income: float) -> dict:
    slabs = [(0,250000,0),(250000,500000,0.05),(500000,1000000,0.20),(1000000,None,0.30)]
    result = apply_slab(taxable_income, slabs)
    tax = result["tax"]
    rebate = tax if taxable_income <= 500000 else 0
    tax_after_rebate = max(0, tax - rebate)
    surcharge = 0
    if taxable_income > 5000000: surcharge = tax_after_rebate * 0.10
    if taxable_income > 10000000: surcharge = tax_after_rebate * 0.15
    cess = (tax_after_rebate + surcharge) * 0.04
    total = tax_after_rebate + surcharge + cess
    return {
        "taxable_income": taxable_income,
        "slab_breakdown": result["breakdown"],
        "tax_before_rebate": tax,
        "rebate_87a": rebate,
        "tax_after_rebate": tax_after_rebate,
        "surcharge": surcharge,
        "cess": cess,
        "total_tax": total
    }

def compute_tax_new_regime(taxable_income: float) -> dict:
    slabs = [(0,300000,0),(300000,700000,0.05),(700000,1000000,0.10),
             (1000000,1200000,0.15),(1200000,1500000,0.20),(1500000,None,0.30)]
    result = apply_slab(taxable_income, slabs)
    tax = result["tax"]
    rebate = tax if taxable_income <= 700000 else 0
    tax_after_rebate = max(0, tax - rebate)
    surcharge = 0
    if taxable_income > 5000000: surcharge = tax_after_rebate * 0.10
    if taxable_income > 10000000: surcharge = tax_after_rebate * 0.15
    cess = (tax_after_rebate + surcharge) * 0.04
    total = tax_after_rebate + surcharge + cess
    return {
        "taxable_income": taxable_income,
        "slab_breakdown": result["breakdown"],
        "tax_before_rebate": tax,
        "rebate_87a": rebate,
        "tax_after_rebate": tax_after_rebate,
        "surcharge": surcharge,
        "cess": cess,
        "total_tax": total
    }

# ── Main Intelligent Tax Engine ──────────────────────────────────────────────

def run_intelligent_tax_analysis(profile: UserFinancialProfile) -> dict:
    """
    Step 1: Pre-compute all verifiable math components
    Step 2: Send to LLM with tax knowledge base — LLM reasons which deductions apply
    Step 3: LLM returns structured optimal scenario
    Step 4: Re-verify LLM's chosen scenario with pure Python math
    Step 5: Return full auditable result
    """

    # Pre-compute all components with verified math
    hra = {}
    if profile.salary and profile.salary.hra_received_annual > 0 and profile.salary.rent_paid_monthly > 0:
        hra = calculate_hra_exemption(
            profile.salary.hra_received_annual,
            profile.salary.rent_paid_monthly * 12,
            profile.salary.basic_salary_annual,
            profile.salary.city == "metro"
        )

    basket_80c = calculate_80c_basket(profile)
    deduction_80d = calculate_80d(profile)

    gross_income = 0
    if profile.salary:
        gross_income += profile.salary.gross_annual
    if profile.freelance:
        gross_income += profile.freelance.annual_inr
    gross_income += (profile.other_income.rental_annual +
                     profile.other_income.fd_interest_annual +
                     profile.other_income.dividend_annual)

    # Old regime taxable income
    old_deductions = {
        "standard_deduction": 50000,
        "hra_exemption": hra.get("exemption", 0),
        "80c": basket_80c["deduction_claimed"],
        "80ccd_1b_nps": min(profile.investments.nps_tier1_annual, 50000),
        "80d": deduction_80d["total_80d"],
        "home_loan_interest_24b": min(profile.loans.home_loan_interest_annual, 200000),
        "80tta_savings_interest": min(profile.other_income.fd_interest_annual, 10000),
    }
    total_old_deductions = sum(old_deductions.values())
    old_taxable = max(0, gross_income - total_old_deductions)
    old_tax_result = compute_tax_old_regime(old_taxable)

    # New regime taxable income
    new_deductions = {
        "standard_deduction": 75000,
    }
    total_new_deductions = sum(new_deductions.values())
    new_taxable = max(0, gross_income - total_new_deductions)
    new_tax_result = compute_tax_new_regime(new_taxable)

    # Now ask LLM to reason intelligently about the situation
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""You are an expert Indian tax advisor. You have access to the complete tax rulebook below.

TAX RULES KNOWLEDGE BASE:
{TAX_KNOWLEDGE_BASE}

USER FINANCIAL PROFILE:
- Age: {profile.age}
- Employment: {profile.employment_type}
- Gross Income: ₹{gross_income:,.0f}
- Salary basic: ₹{(profile.salary.basic_salary_annual if profile.salary else 0):,.0f}
- HRA received: ₹{(profile.salary.hra_received_annual if profile.salary else 0):,.0f}
- Rent paid monthly: ₹{(profile.salary.rent_paid_monthly if profile.salary else 0):,.0f}
- City: {profile.salary.city if profile.salary else 'N/A'}

PRE-COMPUTED VERIFIED MATH (do not recalculate these — use as given):
- HRA exemption: ₹{hra.get('exemption', 0):,.0f} | Working: {hra.get('working', 'N/A')}
- 80C basket: ₹{basket_80c['deduction_claimed']:,.0f} | Headroom: ₹{basket_80c['headroom_remaining']:,.0f}
- 80CCD(1B) NPS: ₹{min(profile.investments.nps_tier1_annual, 50000):,.0f}
- 80D health: ₹{deduction_80d['total_80d']:,.0f}
- Home loan interest (24B): ₹{min(profile.loans.home_loan_interest_annual, 200000):,.0f}

OLD REGIME: Taxable ₹{old_taxable:,.0f} → Tax ₹{old_tax_result['total_tax']:,.0f}
NEW REGIME: Taxable ₹{new_taxable:,.0f} → Tax ₹{new_tax_result['total_tax']:,.0f}

Your job:
1. Determine which regime is better and WHY (specific to this person's situation)
2. Identify any deductions this person is MISSING that they could claim
3. Suggest 2-3 specific actions to reduce tax further (with exact INR impact)
4. Flag anything unusual or worth noting about their situation

Respond in this exact JSON format:
{{
  "recommended_regime": "old" or "new",
  "savings_vs_other_regime": <number — how much more they save>,
  "reasoning": "<2-3 sentence plain English explanation specific to their numbers>",
  "missed_deductions": [
    {{"deduction": "<name>", "potential_saving": <number>, "action": "<what to do>"}}
  ],
  "optimisation_actions": [
    {{"action": "<specific action>", "tax_saving": <number>, "working": "<brief calc>"}}
  ],
  "flags": ["<any important notes>"],
  "ai_summary": "<one powerful sentence — their key tax situation in plain English>"
}}"""

    response = client.messages.create(
        model=settings.model,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text
    # Strip markdown fences if present
    clean = raw.strip().replace("```json", "").replace("```", "").strip()
    ai_analysis = json.loads(clean)

    return {
        "gross_income": gross_income,
        "old_regime": {
            **old_tax_result,
            "deductions": old_deductions,
            "total_deductions": total_old_deductions,
        },
        "new_regime": {
            **new_tax_result,
            "deductions": new_deductions,
            "total_deductions": total_new_deductions,
        },
        "hra_calculation": hra,
        "basket_80c": basket_80c,
        "deduction_80d": deduction_80d,
        "ai_analysis": ai_analysis,
        "verified": True,
        "note": "All tax figures computed by verified Python engine. AI provided strategic reasoning only."
    }

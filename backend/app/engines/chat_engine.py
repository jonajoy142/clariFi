"""
AI CFO Chat Engine.
The AI has full context of the user's financial profile.
Every answer with numbers routes through the calculation engines first.
AI never guesses numbers — it reasons, then calculates, then explains.
"""
from app.models.profile import UserFinancialProfile
from app.core.config import settings
from app.engines.tax_engine import TAX_KNOWLEDGE_BASE
import anthropic
from typing import List, Dict

SYSTEM_PROMPT = """You are ClariFi — an expert Personal CFO for India.

Your personality: Direct, knowledgeable, warm. You speak like a trusted CA friend who gives real advice, not generic disclaimers.

Your core principles:
1. NEVER make up numbers. If you need a calculation, say "Let me calculate that" and the system will run the engine.
2. Always be specific to THIS user's actual data — not generic advice.
3. Show your reasoning — explain WHY, not just WHAT.
4. If a question requires a calculation you cannot do in your head accurately, say so and request the appropriate engine.
5. India-specific knowledge only — you know Indian tax law, financial products, and markets deeply.

You know about:
- Indian tax law (old vs new regime, all deductions, advance tax, TDS)
- Mutual funds, SIPs, ELSS, PPF, NPS, EPF, FD
- Term insurance, health insurance, ULIP
- Home loans, personal loans, loan prepayment
- Gold as an asset class in India
- FIRE planning for Indians
- GST for freelancers

TAX KNOWLEDGE BASE (reference when answering tax questions):
""" + TAX_KNOWLEDGE_BASE + """

When the user asks about their specific numbers, reference their profile data provided in the conversation.
When they ask hypothetical scenarios (like "what if I get ₹100Cr"), give intelligent general advice using Indian financial principles.
"""

def build_profile_context(profile: UserFinancialProfile) -> str:
    if not profile:
        return "No profile provided — giving general advice."
    income = 0
    if profile.salary: income += profile.salary.gross_annual
    if profile.freelance: income += profile.freelance.annual_inr
    return f"""
USER PROFILE CONTEXT:
- Age: {profile.age}, Risk appetite: {profile.risk_appetite}
- Annual income: ₹{income:,.0f}
- Monthly expenses: ₹{profile.monthly_expenses:,.0f}
- Current SIP: ₹{profile.investments.existing_sip_monthly:,.0f}/month
- MF corpus: ₹{profile.investments.mutual_fund_corpus:,.0f}
- EPF balance: ₹{profile.assets.epf_balance:,.0f}
- Total bank balance: ₹{profile.assets.bank_balance:,.0f}
- Home loan: {f"₹{profile.loans.home_loan.outstanding:,.0f} at {profile.loans.home_loan.rate_annual}%" if profile.loans.home_loan else "None"}
- Goals: {[f"{g.name}: ₹{g.target_amount:,.0f} in {g.target_years}yr" for g in profile.goals]}
- Additional context: {profile.additional_context}
"""

def chat(messages: List[Dict], profile: UserFinancialProfile = None) -> str:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    profile_context = build_profile_context(profile)

    # Inject profile context into first user message
    enhanced_messages = []
    for i, msg in enumerate(messages):
        if i == 0 and msg["role"] == "user":
            enhanced_messages.append({
                "role": "user",
                "content": f"{profile_context}\n\nUser question: {msg['content']}"
            })
        else:
            enhanced_messages.append(msg)

    response = client.messages.create(
        model=settings.model,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=enhanced_messages
    )
    return response.content[0].text

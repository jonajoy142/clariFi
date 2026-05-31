from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    source_type: str
    source_id: str
    title: str
    excerpt: str
    amount: Decimal | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RiskFinding(BaseModel):
    title: str
    severity: Literal["low", "medium", "high", "critical"]
    financial_impact: Decimal | None = None
    explanation: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: Decimal = Decimal("0.85")


class RecommendationOutput(BaseModel):
    title: str
    issue: str
    impact: str
    recommended_action: str
    confidence: Decimal
    evidence: list[EvidenceItem] = Field(default_factory=list)
    financial_impact_amount: Decimal | None = None
    requires_approval: bool = True


class CFOBriefing(BaseModel):
    title: str
    what_changed: list[str]
    risks: list[RiskFinding]
    recommended_actions: list[RecommendationOutput]
    evidence: list[EvidenceItem]
    confidence: Decimal = Decimal("0.85")


class ActionDraft(BaseModel):
    action_type: str
    title: str
    body: str
    requires_approval: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    passed: bool
    reason: str
    unsupported_numbers: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)


class FinancialContextPack(BaseModel):
    organization_id: str
    user_type: Literal["startup", "freelancer"]
    question: str | None = None
    cash_position: dict[str, Any] = Field(default_factory=dict)
    runway: dict[str, Any] = Field(default_factory=dict)
    burn_rate: dict[str, Any] = Field(default_factory=dict)
    receivables: dict[str, Any] = Field(default_factory=dict)
    payables: dict[str, Any] = Field(default_factory=dict)
    simulations: dict[str, Any] = Field(default_factory=dict)
    operations: dict[str, Any] = Field(default_factory=dict)
    top_risks: list[RiskFinding] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    allowed_numbers: list[Decimal] = Field(default_factory=list)
    source_fact_ids: list[str] = Field(default_factory=list)


class ChatAnswer(BaseModel):
    answer: str
    tools_used: list[str]
    evidence: list[EvidenceItem]
    verification: VerificationResult
    context_pack: FinancialContextPack

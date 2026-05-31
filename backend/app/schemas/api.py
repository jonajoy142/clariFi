from datetime import datetime
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class DevLoginRequest(BaseModel):
    user_type: Literal["startup", "freelancer"] = "startup"


class DevLoginResponse(BaseModel):
    user_id: str
    organization_id: str
    user_type: str
    email: str


class OrganizationResponse(BaseModel):
    id: str
    name: str
    user_type: str
    currency: str
    settings: dict[str, Any]


class ConnectorResponse(BaseModel):
    id: str
    type: str
    status: str
    last_synced_at: datetime | None = None


class DashboardSummary(BaseModel):
    organization: OrganizationResponse
    metrics: dict[str, Any]
    top_risks: list[dict[str, Any]]
    recommended_actions: list[dict[str, Any]]
    facts: list[dict[str, Any]]


class RecommendationResponse(BaseModel):
    id: str
    title: str
    issue: str
    impact: str
    recommended_action: str
    confidence_score: Decimal
    status: str
    evidence: list[dict[str, Any]]
    financial_impact_amount: Decimal | None
    source_fact_ids: list[str]


class AlertResponse(BaseModel):
    id: str
    severity: str
    title: str
    message: str
    status: str
    evidence: list[dict[str, Any]]


class HiringSimulationRequest(BaseModel):
    role: str = "Engineer"
    monthly_cost: Decimal = Field(..., gt=0)
    benefits_multiplier: Decimal = Field(Decimal("1.18"), gt=0)
    equipment_cost: Decimal = Field(Decimal("120000"), ge=0)
    software_seat_cost: Decimal = Field(Decimal("12000"), ge=0)
    recruiting_onboarding_cost: Decimal = Field(Decimal("50000"), ge=0)
    start_date: date | None = None


class VendorCutSimulationRequest(BaseModel):
    vendor_name: str
    monthly_savings: Decimal = Field(..., gt=0)
    cancellation_date: date | None = None
    operational_risk_note: str = "Review owner impact before cancelling."


class SimulationResponse(BaseModel):
    runway_before: Decimal
    runway_after: Decimal
    burn_before: Decimal
    burn_after: Decimal
    risk_level: str
    evidence: list[dict[str, Any]]


class ChatRequest(BaseModel):
    question: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    thread_id: str
    tools_used: list[str]
    evidence: list[dict[str, Any]]
    audit_log_id: str
    verification: dict[str, Any]


class DocumentUploadRequest(BaseModel):
    title: str
    document_type: str = "note"
    text: str
    source: str = "manual"


class DocumentSearchResponse(BaseModel):
    items: list[dict[str, Any]]

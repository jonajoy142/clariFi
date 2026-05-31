from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MoneyFact(BaseModel):
    fact_type: str
    value: Decimal
    currency: str = "INR"
    period_start: date | None = None
    period_end: date | None = None
    formula: str
    source_record_ids: list[str] = Field(default_factory=list)
    engine_name: str
    engine_version: str
    confidence_score: Decimal = Decimal("1.0")


class Evidence(BaseModel):
    source_type: str
    source_id: str
    title: str
    excerpt: str
    amount: Decimal | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditLogRead(ORMModel):
    id: str
    event_type: str
    entity_type: str
    action: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    prompt_version: str | None = None
    model_used: str | None = None
    verification_status: str
    created_at: datetime


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int


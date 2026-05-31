from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalizedPayload:
    accounts: list[dict[str, Any]] = field(default_factory=list)
    transactions: list[dict[str, Any]] = field(default_factory=list)
    invoices: list[dict[str, Any]] = field(default_factory=list)
    customers: list[dict[str, Any]] = field(default_factory=list)
    vendors: list[dict[str, Any]] = field(default_factory=list)
    subscriptions: list[dict[str, Any]] = field(default_factory=list)
    payroll_items: list[dict[str, Any]] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)


class Connector(ABC):
    type: str
    display_name: str

    @abstractmethod
    def connect(self, organization_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def sync(self, organization_id: str, user_type: str) -> NormalizedPayload:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> NormalizedPayload:
        raise NotImplementedError

    @abstractmethod
    def get_status(self, organization_id: str) -> dict[str, Any]:
        raise NotImplementedError


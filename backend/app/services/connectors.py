from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.mock import get_connector
from app.models.finance import (
    BankAccount,
    ConnectorStatus,
    Customer,
    Invoice,
    PayrollItem,
    Subscription,
    Transaction,
    Vendor,
)
from app.repositories.finance import ConnectorRepository, OrganizationRepository
from app.services.documents import DocumentService
from app.services.facts import FinancialFactService
from app.services.recommendations import RecommendationService


class ConnectorService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ConnectorRepository(db)
        self.org_repo = OrganizationRepository(db)

    def connect(self, organization_id: str, connector_type: str):
        org = self.org_repo.get(organization_id)
        if org is None:
            raise ValueError("Organization not found")
        if not self._is_available_for_user_type(connector_type, org.user_type):
            raise ValueError(f"{connector_type} is not available for {org.user_type} organizations")
        adapter = get_connector(connector_type)
        adapter.connect(organization_id)
        connector = self.repo.get_or_create(organization_id, connector_type)
        connector.status = ConnectorStatus.mock_connected.value
        connector.config = {"mode": "mock", "display_name": adapter.display_name}
        self.db.commit()
        return connector

    def sync(self, organization_id: str, connector_id: str) -> dict[str, Any]:
        connector = self.repo.get(connector_id)
        org = self.org_repo.get(organization_id)
        if connector is None or org is None or connector.organization_id != organization_id:
            raise ValueError("Connector not found")

        connector.status = ConnectorStatus.syncing.value
        job = self.repo.create_sync_job(organization_id, connector.id, status="running")
        self.db.flush()
        adapter = get_connector(connector.type)
        payload = adapter.sync(organization_id, org.user_type)
        stats = self._persist_payload(organization_id, payload)
        connector.status = ConnectorStatus.mock_connected.value
        connector.last_synced_at = datetime.utcnow()
        job.status = "completed"
        job.stats = stats
        FinancialFactService(self.db).calculate_and_persist(organization_id)
        RecommendationService(self.db).regenerate(organization_id)
        self.db.commit()
        return {"connector_id": connector.id, "stats": stats}

    def list(self, organization_id: str):
        return self.repo.list_for_org(organization_id)

    def catalog(self, organization_id: str) -> list[dict[str, Any]]:
        org = self.org_repo.get(organization_id)
        if org is None:
            raise ValueError("Organization not found")
        existing = {connector.type: connector for connector in self.repo.list_for_org(organization_id)}
        result: list[dict[str, Any]] = []
        for connector_type, display_name in _CONNECTOR_CATALOG:
            available = self._is_available_for_user_type(connector_type, org.user_type)
            connector = existing.get(connector_type)
            status = connector.status if connector else ConnectorStatus.not_connected.value
            if connector and connector.config.get("mode") == "mock" and status == ConnectorStatus.connected.value:
                status = ConnectorStatus.mock_connected.value
            if not available:
                status = ConnectorStatus.coming_soon.value
            result.append(
                {
                    "id": connector.id if connector else None,
                    "type": connector_type,
                    "display_name": display_name,
                    "status": status,
                    "last_synced_at": connector.last_synced_at if connector else None,
                    "mode": connector.config.get("mode", "mock") if connector else "mock",
                    "available": available,
                    "implemented": available,
                    "description": _connector_description(connector_type, org.user_type, available),
                }
            )
        return result

    def _is_available_for_user_type(self, connector_type: str, user_type: str) -> bool:
        if connector_type == "zoho_books" and user_type != "startup":
            return False
        return connector_type in {"zoho_books", "stripe", "razorpay", "gmail", "google_drive", "manual_csv"}

    def _persist_payload(self, organization_id: str, payload) -> dict[str, int]:
        stats = {
            "accounts": 0,
            "transactions": 0,
            "invoices": 0,
            "customers": 0,
            "vendors": 0,
            "subscriptions": 0,
            "payroll_items": 0,
            "documents": 0,
        }
        customers = self._upsert_customers(organization_id, payload.customers)
        vendors = self._upsert_vendors(organization_id, payload.vendors)
        stats["customers"] = len(customers)
        stats["vendors"] = len(vendors)

        for account in payload.accounts:
            if not self.db.scalar(select(BankAccount).where(BankAccount.organization_id == organization_id, BankAccount.account_name == account["account_name"])):
                self.db.add(BankAccount(organization_id=organization_id, **account))
                stats["accounts"] += 1

        for invoice in payload.invoices:
            if self.db.scalar(select(Invoice).where(Invoice.organization_id == organization_id, Invoice.invoice_number == invoice["invoice_number"])):
                continue
            customer_id = customers.get(invoice.pop("customer_name", None))
            vendor_id = vendors.get(invoice.pop("vendor_name", None))
            self.db.add(Invoice(organization_id=organization_id, customer_id=customer_id, vendor_id=vendor_id, **invoice))
            stats["invoices"] += 1

        for subscription in payload.subscriptions:
            if self.db.scalar(select(Subscription).where(Subscription.organization_id == organization_id, Subscription.name == subscription["name"], Subscription.monthly_amount == subscription["monthly_amount"])):
                continue
            vendor_id = vendors.get(subscription["name"])
            self.db.add(Subscription(organization_id=organization_id, vendor_id=vendor_id, **subscription))
            stats["subscriptions"] += 1

        for payroll in payload.payroll_items:
            if self.db.scalar(select(PayrollItem).where(PayrollItem.organization_id == organization_id, PayrollItem.employee_name == payroll["employee_name"])):
                continue
            self.db.add(PayrollItem(organization_id=organization_id, **payroll))
            stats["payroll_items"] += 1

        self.db.flush()
        for transaction in payload.transactions:
            vendor_id = vendors.get(transaction.pop("vendor_name", None))
            if self.db.scalar(select(Transaction).where(Transaction.organization_id == organization_id, Transaction.description == transaction["description"], Transaction.occurred_on == transaction["occurred_on"], Transaction.amount == transaction["amount"])):
                continue
            self.db.add(Transaction(organization_id=organization_id, vendor_id=vendor_id, **transaction))
            stats["transactions"] += 1

        doc_service = DocumentService(self.db)
        for doc in payload.documents:
            doc_service.ingest(organization_id, title=doc["title"], text=doc["text"], document_type=doc.get("document_type", "note"), source=doc.get("source", "manual"))
            stats["documents"] += 1
        self.db.flush()
        return stats

    def _upsert_customers(self, organization_id: str, items: list[dict[str, Any]]) -> dict[str, str]:
        result: dict[str, str] = {}
        for item in items:
            customer = self.db.scalar(select(Customer).where(Customer.organization_id == organization_id, Customer.name == item["name"]))
            if customer is None:
                customer = Customer(organization_id=organization_id, **item)
                self.db.add(customer)
                self.db.flush()
            result[customer.name] = customer.id
        return result

    def _upsert_vendors(self, organization_id: str, items: list[dict[str, Any]]) -> dict[str, str]:
        result: dict[str, str] = {}
        for item in items:
            vendor = self.db.scalar(select(Vendor).where(Vendor.organization_id == organization_id, Vendor.name == item["name"]))
            if vendor is None:
                vendor = Vendor(organization_id=organization_id, **item)
                self.db.add(vendor)
                self.db.flush()
            result[vendor.name] = vendor.id
        return result


_CONNECTOR_CATALOG = [
    ("zoho_books", "Zoho Books"),
    ("stripe", "Stripe"),
    ("razorpay", "Razorpay"),
    ("gmail", "Gmail"),
    ("google_drive", "Google Drive"),
    ("manual_csv", "Manual CSV"),
]


def _connector_description(connector_type: str, user_type: str, available: bool) -> str:
    if not available:
        return f"{connector_type.replace('_', ' ').title()} is not part of the {user_type} MVP connector set."
    if connector_type in {"gmail", "google_drive"}:
        return "Mock document connector. Real OAuth can be added behind this adapter."
    if connector_type == "manual_csv":
        return "Manual fallback seeded through the same normalization layer."
    return "Mock finance connector using production connect/sync/normalize boundaries."

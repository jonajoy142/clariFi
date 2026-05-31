from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.connectors.base import Connector, NormalizedPayload


class MockConnector(Connector):
    type = "mock"
    display_name = "Mock Connector"

    def connect(self, organization_id: str) -> dict[str, Any]:
        return {"organization_id": organization_id, "status": "connected", "mode": "mock"}

    def sync(self, organization_id: str, user_type: str) -> NormalizedPayload:
        return self.normalize({"user_type": user_type})

    def normalize(self, raw: dict[str, Any]) -> NormalizedPayload:
        return NormalizedPayload()

    def get_status(self, organization_id: str) -> dict[str, Any]:
        return {"organization_id": organization_id, "status": "connected"}


class MockZohoBooksConnector(MockConnector):
    type = "zoho_books"
    display_name = "Zoho Books"

    def normalize(self, raw: dict[str, Any]) -> NormalizedPayload:
        if raw.get("user_type") == "freelancer":
            return NormalizedPayload()
        today = date.today()
        return NormalizedPayload(
            invoices=[
                {
                    "invoice_number": "INV-STARTUP-1042",
                    "direction": "receivable",
                    "amount": Decimal("180000"),
                    "paid_amount": Decimal("0"),
                    "issued_on": today - timedelta(days=48),
                    "due_on": today - timedelta(days=18),
                    "status": "overdue",
                    "customer_name": "Northstar Labs",
                    "source": self.type,
                },
                {
                    "invoice_number": "BILL-AWS-0526",
                    "direction": "payable",
                    "amount": Decimal("69000"),
                    "paid_amount": Decimal("0"),
                    "issued_on": today - timedelta(days=5),
                    "due_on": today + timedelta(days=8),
                    "status": "sent",
                    "vendor_name": "AWS",
                    "source": self.type,
                },
            ],
            customers=[{"name": "Northstar Labs", "email": "finance@northstar.example", "average_payment_delay_days": 12}],
            vendors=[{"name": "AWS", "category": "cloud", "is_saas": True}],
        )


class MockStripeConnector(MockConnector):
    type = "stripe"
    display_name = "Stripe"

    def normalize(self, raw: dict[str, Any]) -> NormalizedPayload:
        today = date.today()
        if raw.get("user_type") == "freelancer":
            return NormalizedPayload(
                transactions=[
                    {"amount": Decimal("125000"), "occurred_on": today - timedelta(days=12), "description": "Stripe client payment", "category": "stripe_revenue", "source": self.type},
                    {"amount": Decimal("-12000"), "occurred_on": today - timedelta(days=10), "description": "Stripe processing fees", "category": "payment_fees", "source": self.type},
                ]
            )
        return NormalizedPayload(
            transactions=[
                {"amount": Decimal("340000"), "occurred_on": today - timedelta(days=12), "description": "Stripe SaaS revenue", "category": "stripe_revenue", "source": self.type},
                {"amount": Decimal("-8000"), "occurred_on": today - timedelta(days=12), "description": "Stripe processing fees", "category": "payment_fees", "source": self.type},
            ]
        )


class MockRazorpayConnector(MockConnector):
    type = "razorpay"
    display_name = "Razorpay"

    def normalize(self, raw: dict[str, Any]) -> NormalizedPayload:
        today = date.today()
        return NormalizedPayload(
            transactions=[
                {"amount": Decimal("110000"), "occurred_on": today - timedelta(days=8), "description": "Razorpay subscription revenue", "category": "razorpay_revenue", "source": self.type},
                {"amount": Decimal("-5000"), "occurred_on": today - timedelta(days=8), "description": "Razorpay fees", "category": "payment_fees", "source": self.type},
            ]
        )


class MockGmailConnector(MockConnector):
    type = "gmail"
    display_name = "Gmail"

    def normalize(self, raw: dict[str, Any]) -> NormalizedPayload:
        user_type = raw.get("user_type")
        if user_type == "freelancer":
            return NormalizedPayload(
                documents=[
                    {
                        "title": "Follow-up context for Acme Design invoice",
                        "document_type": "email",
                        "text": "Acme Design has paid late twice before. Last promise said payment would clear by Friday.",
                        "source": self.type,
                    }
                ]
            )
        return NormalizedPayload(
            documents=[
                {
                    "title": "AWS renewal notice",
                    "document_type": "email",
                    "text": "AWS usage increased after enabling production analytics jobs. Finance should review compute commitments.",
                    "source": self.type,
                }
            ]
        )


class MockGoogleDriveConnector(MockConnector):
    type = "google_drive"
    display_name = "Google Drive"

    def normalize(self, raw: dict[str, Any]) -> NormalizedPayload:
        return NormalizedPayload(
            documents=[
                {
                    "title": "Finance operating policy",
                    "document_type": "policy",
                    "text": "All irreversible finance actions require approval. AI may draft messages but must not send payments or emails without user approval.",
                    "source": self.type,
                }
            ]
        )


class MockManualCSVConnector(MockConnector):
    type = "manual_csv"
    display_name = "Manual CSV"

    def normalize(self, raw: dict[str, Any]) -> NormalizedPayload:
        today = date.today()
        if raw.get("user_type") == "freelancer":
            return NormalizedPayload(
                accounts=[{"provider": "manual", "account_name": "Primary Current Account", "current_balance": Decimal("240000")}],
                invoices=[
                    {
                        "invoice_number": "INV-FREE-221",
                        "direction": "receivable",
                        "amount": Decimal("42000"),
                        "paid_amount": Decimal("0"),
                        "issued_on": today - timedelta(days=48),
                        "due_on": today - timedelta(days=18),
                        "status": "overdue",
                        "customer_name": "Acme Design",
                        "source": self.type,
                    }
                ],
                customers=[{"name": "Acme Design", "email": "accounts@acme.example", "average_payment_delay_days": 18}],
                vendors=[
                    {"name": "Figma", "category": "software", "is_saas": True},
                    {"name": "Notion", "category": "software", "is_saas": True},
                ],
                subscriptions=[
                    {"name": "Figma", "monthly_amount": Decimal("4800"), "status": "active"},
                    {"name": "Notion", "monthly_amount": Decimal("1600"), "status": "active"},
                ],
                transactions=[
                    {"amount": Decimal("-38000"), "occurred_on": today - timedelta(days=3), "description": "Contractor design support", "category": "project_expense", "source": self.type},
                    {"amount": Decimal("-4800"), "occurred_on": today - timedelta(days=6), "description": "Figma subscription", "category": "software", "source": self.type, "vendor_name": "Figma"},
                    {"amount": Decimal("-1600"), "occurred_on": today - timedelta(days=7), "description": "Notion subscription", "category": "software", "source": self.type, "vendor_name": "Notion"},
                ],
            )
        return NormalizedPayload(
            accounts=[{"provider": "manual", "account_name": "Operating Account", "current_balance": Decimal("2300000")}],
            vendors=[
                {"name": "AWS", "category": "cloud", "is_saas": True},
                {"name": "Linear", "category": "software", "is_saas": True},
                {"name": "OpenAI", "category": "ai_infra", "is_saas": True},
            ],
            subscriptions=[
                {"name": "Linear", "monthly_amount": Decimal("8000"), "status": "active"},
                {"name": "OpenAI", "monthly_amount": Decimal("15000"), "status": "active"},
                {"name": "OpenAI", "monthly_amount": Decimal("5000"), "status": "active"},
            ],
            payroll_items=[
                {"employee_name": "Founding Engineer", "role": "Engineering", "monthly_cost": Decimal("60000"), "active": True},
                {"employee_name": "Growth Lead", "role": "Growth", "monthly_cost": Decimal("40000"), "active": True},
            ],
            transactions=[
                {"amount": Decimal("-50000"), "occurred_on": today - timedelta(days=45), "description": "AWS previous month", "category": "cloud", "source": self.type, "vendor_name": "AWS"},
                {"amount": Decimal("-69000"), "occurred_on": today - timedelta(days=9), "description": "AWS current month", "category": "cloud", "source": self.type, "vendor_name": "AWS"},
                {"amount": Decimal("-8000"), "occurred_on": today - timedelta(days=5), "description": "Linear subscription", "category": "software", "source": self.type, "vendor_name": "Linear"},
                {"amount": Decimal("-20000"), "occurred_on": today - timedelta(days=4), "description": "OpenAI API and duplicate workspace", "category": "ai_infra", "source": self.type, "vendor_name": "OpenAI"},
            ],
        )


CONNECTOR_REGISTRY: dict[str, type[MockConnector]] = {
    "zoho_books": MockZohoBooksConnector,
    "stripe": MockStripeConnector,
    "razorpay": MockRazorpayConnector,
    "gmail": MockGmailConnector,
    "google_drive": MockGoogleDriveConnector,
    "manual_csv": MockManualCSVConnector,
}


def get_connector(connector_type: str) -> MockConnector:
    connector_cls = CONNECTOR_REGISTRY.get(connector_type)
    if connector_cls is None:
        raise ValueError(f"Unsupported connector type: {connector_type}")
    return connector_cls()

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.engines.base import EngineOutput, FactResult, money


class VendorWasteEngine:
    name = "VendorWasteEngine"
    version = "1.0.0"

    def calculate(self, vendors: list, subscriptions: list, transactions: list, as_of: date | None = None) -> EngineOutput:
        as_of = as_of or date.today()
        active_subs = [sub for sub in subscriptions if sub.status == "active"]
        recurring_total = sum((money(sub.monthly_amount) for sub in active_subs), Decimal("0.00"))
        by_vendor: dict[str, list] = defaultdict(list)
        for sub in active_subs:
            by_vendor[sub.name.lower().replace(" ", "")].append(sub)
        duplicate_subs = [subs for subs in by_vendor.values() if len(subs) > 1]
        duplicate_waste = sum((money(sub.monthly_amount) for subs in duplicate_subs for sub in subs[1:]), Decimal("0.00"))

        current_start = as_of - timedelta(days=30)
        previous_start = as_of - timedelta(days=60)
        vendor_spikes: list[dict] = []
        for vendor in vendors:
            current = abs(sum((money(txn.amount) for txn in transactions if txn.vendor_id == vendor.id and current_start <= txn.occurred_on <= as_of and money(txn.amount) < 0), Decimal("0.00")))
            previous = abs(sum((money(txn.amount) for txn in transactions if txn.vendor_id == vendor.id and previous_start <= txn.occurred_on < current_start and money(txn.amount) < 0), Decimal("0.00")))
            if previous and current > previous * Decimal("1.25"):
                vendor_spikes.append({
                    "vendor_id": vendor.id,
                    "vendor_name": vendor.name,
                    "previous": float(previous),
                    "current": float(current),
                    "increase_percent": float(((current - previous) / previous * Decimal("100")).quantize(Decimal("0.01"))),
                })

        return EngineOutput(
            engine_name=self.name,
            engine_version=self.version,
            facts=[
                FactResult(
                    fact_type="recurring_subscriptions_monthly",
                    value=money(recurring_total),
                    formula="sum(active subscriptions.monthly_amount)",
                    source_record_ids=[sub.id for sub in active_subs],
                ),
                FactResult(
                    fact_type="duplicate_vendor_waste_monthly",
                    value=money(duplicate_waste),
                    formula="sum(duplicate active subscription monthly_amount beyond first vendor instance)",
                    source_record_ids=[sub.id for subs in duplicate_subs for sub in subs[1:]],
                ),
            ],
            details={"vendor_spikes": vendor_spikes, "duplicate_subscription_groups": len(duplicate_subs)},
        )


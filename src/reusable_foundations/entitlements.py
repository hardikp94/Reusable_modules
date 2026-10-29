"""Receipt-derived subscriptions and atomic usage/credit ledgers."""
import hashlib
import json
import time


class AllowanceError(ValueError):
    pass


class Subscriptions:
    def __init__(self, store, gateway, plans, *, clock=time.time):
        self.store, self.gateway, self.plans, self.clock = store, gateway, plans, clock

    def create(self, owner, plan, request_id):
        binding = self.plans[plan]
        key = self.gateway.mode + ":" + hashlib.sha256(json.dumps([owner, request_id]).encode()).hexdigest()
        with self.store.transaction():
            row = self.store.get("subscriptions", key)
            if row:
                if row["plan"] != plan or not row.get("provider_id"):
                    raise AllowanceError("Creation requires reconciliation")
                return row
            row = {"id": key, "owner": owner, "plan": plan, "state": "creating", "paid_until": 0, "cancel_at_end": False}
            self.store.put("subscriptions", key, row)
        result = self.gateway.create_subscription(binding["provider_plan"], total_count=binding["total_count"])
        if result.get("plan_id") != binding["provider_plan"] or not result.get("id"):
            raise AllowanceError("Subscription binding mismatch")
        row.update(provider_id=result["id"], state=result["status"])
        self.store.put("subscriptions", key, row)
        return row

    def reconcile(self, owner, subscription_id):
        row = self._owned(owner, subscription_id)
        remote = self.gateway.subscription(row["provider_id"])
        if remote.get("id") != row["provider_id"] or remote.get("plan_id") != self.plans[row["plan"]]["provider_plan"]:
            raise AllowanceError("Subscription binding mismatch")
        # Provider state alone never creates a paid period.
        with self.store.transaction():
            row = self._owned(owner, subscription_id)
            row.update(state=remote["status"], cancel_at_end=bool(remote.get("cancel_at_cycle_end")))
            self.store.put("subscriptions", row["id"], row)
        return row

    def record_paid_period(self, owner, subscription_id, invoice_id):
        row = self._owned(owner, subscription_id)
        invoice = self.gateway.invoice(invoice_id)
        payment_id = invoice.get("payment_id")
        if invoice.get("subscription_id") != row["provider_id"] or invoice.get("status") != "paid" or not payment_id:
            raise AllowanceError("Unverified subscription invoice")
        payment = self.gateway.payment(payment_id)
        plan = self.plans[row["plan"]]
        if payment.get("id") != payment_id or payment.get("invoice_id") != invoice_id or payment.get("status") != "captured" or payment.get("amount") != plan["amount"] or payment.get("currency") != plan["currency"] or payment.get("amount_refunded", 0) != 0 or invoice.get("amount_paid") != plan["amount"] or invoice.get("currency") != plan["currency"]:
            raise AllowanceError("Unverified subscription payment")
        start, end = invoice.get("billing_start"), invoice.get("billing_end")
        if type(start) is not int or type(end) is not int or not 0 <= start < end:
            raise AllowanceError("Invalid paid period")
        key = self.gateway.mode + ":" + payment_id
        with self.store.transaction():
            previous = self.store.get("subscription_receipts", key)
            receipt = {"subscription": row["id"], "start": start, "end": end, "invoice": invoice_id}
            if previous and {k: v for k, v in previous.items() if k != "revoked"} != receipt:
                raise AllowanceError("Payment already bound to another period")
            if previous and previous.get("revoked"):
                raise AllowanceError("Payment revoked")
            self.store.put("subscription_receipts", key, receipt)
            row = self._owned(owner, subscription_id)
            row["paid_until"] = max(row["paid_until"], end)
            self.store.put("subscriptions", row["id"], row)

    def cancel(self, owner, subscription_id):
        row = self._owned(owner, subscription_id)
        self.gateway.cancel_subscription(row["provider_id"])
        return self.reconcile(owner, subscription_id)

    def allows(self, owner, subscription_id, feature):
        row = self._owned(owner, subscription_id)
        return row["state"] in {"active", "cancelled", "completed"} and any(r["subscription"] == row["id"] and r["start"] <= self.clock() < r["end"] and not r.get("revoked", False) for r in self.store.all("subscription_receipts")) and feature in self.plans[row["plan"]].get("features", [])

    def revoke_payment(self, owner, subscription_id, payment_id):
        row = self._owned(owner, subscription_id)
        key = self.gateway.mode + ":" + payment_id
        with self.store.transaction():
            receipt = self.store.get("subscription_receipts", key)
            if not receipt or receipt["subscription"] != row["id"]:
                raise AllowanceError("Receipt not found")
            receipt["revoked"] = True
            self.store.put("subscription_receipts", key, receipt)

    def _owned(self, owner, subscription_id):
        row = self.store.get("subscriptions", subscription_id)
        if not row or row["owner"] != owner or not row["id"].startswith(self.gateway.mode + ":"):
            raise AllowanceError("Subscription not found")
        return row


class Quotas:
    def __init__(self, store, *, clock=time.time):
        self.store, self.clock = store, clock

    def grant(self, owner, grant_id, units, *, expires, kind="credit"):
        if type(units) is not int or units < 1 or expires <= self.clock():
            raise AllowanceError("Invalid grant")
        row = {"id": grant_id, "owner": owner, "limit": units, "used": 0, "reserved": 0, "expires": expires, "kind": kind, "revoked": False}
        with self.store.transaction():
            old = self.store.get("grants", grant_id)
            if old:
                if any(old[k] != row[k] for k in ("owner", "limit", "expires", "kind")):
                    raise AllowanceError("Grant ID already used")
                return old
            self.store.put("grants", grant_id, row)
        return row

    def reserve(self, owner, operation_id, *, units=1, kind=None):
        if type(units) is not int or units < 1:
            raise AllowanceError("Invalid usage")
        key = hashlib.sha256(json.dumps([owner, operation_id]).encode()).hexdigest()
        with self.store.transaction():
            old = self.store.get("reservations", key)
            if old:
                if old["units"] != units or old["kind"] != kind:
                    raise AllowanceError("Operation ID conflict")
                return old
            grants = sorted(self.store.all("grants"), key=lambda r: r["expires"])
            grant = next((g for g in grants if g["owner"] == owner and not g["revoked"] and g["expires"] > self.clock() and (kind is None or kind == g["kind"]) and g["limit"] - g["used"] - g["reserved"] >= units), None)
            if not grant:
                raise AllowanceError("Allowance exhausted")
            grant["reserved"] += units
            row = {"id": key, "owner": owner, "grant": grant["id"], "units": units, "kind": kind, "state": "reserved"}
            self.store.put("grants", grant["id"], grant)
            self.store.put("reservations", key, row)
        return row

    def settle(self, owner, reservation_id, *, success):
        with self.store.transaction():
            row = self.store.get("reservations", reservation_id)
            if not row or row["owner"] != owner:
                raise AllowanceError("Reservation not found")
            target = "consumed" if success else "released"
            if row["state"] != "reserved":
                if row["state"] != target:
                    raise AllowanceError("Already settled differently")
                return row
            grant = self.store.get("grants", row["grant"])
            grant["reserved"] -= row["units"]
            grant["used"] += row["units"] if success else 0
            row["state"] = target
            self.store.put("grants", grant["id"], grant)
            self.store.put("reservations", row["id"], row)
        return row

    def revoke(self, owner, grant_id):
        with self.store.transaction():
            row = self.store.get("grants", grant_id)
            if not row or row["owner"] != owner:
                raise AllowanceError("Grant not found")
            row["revoked"] = True
            self.store.put("grants", grant_id, row)

    def balance(self, owner):
        return sum(max(0, g["limit"] - g["used"] - g["reserved"]) for g in self.store.all("grants") if g["owner"] == owner and not g["revoked"] and g["expires"] > self.clock())

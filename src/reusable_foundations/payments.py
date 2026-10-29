"""Razorpay adapter and durable owned payment records. All amounts are minor units."""
import hashlib
import hmac
import json
import re
import time


class PaymentError(ValueError):
    pass


class Razorpay:
    """Inject a configured official SDK client; no implicit network/credential loading."""
    def __init__(self, client, *, key_id, key_secret, webhook_secret, mode="test"):
        if mode not in {"test", "live"} or not key_id.startswith("rzp_" + mode + "_") or not key_secret or not webhook_secret:
            raise PaymentError("Invalid explicit gateway configuration")
        self.client, self.key_id, self.mode = client, key_id, mode
        self._secret, self._webhook_secret = key_secret, webhook_secret

    def create_order(self, amount, currency, receipt):
        return self.client.order.create(data={"amount": amount, "currency": currency, "receipt": receipt})

    def payment(self, payment_id):
        return self.client.payment.fetch(payment_id)

    def create_subscription(self, plan_id, *, total_count):
        return self.client.subscription.create(data={"plan_id": plan_id, "total_count": total_count, "customer_notify": 1})

    def cancel_subscription(self, subscription_id):
        return self.client.subscription.cancel(subscription_id, {"cancel_at_cycle_end": 1})

    def subscription(self, subscription_id):
        return self.client.subscription.fetch(subscription_id)

    def invoice(self, invoice_id):
        return self.client.invoice.fetch(invoice_id)

    def verify_checkout(self, order_id, payment_id, signature):
        expected = hmac.new(self._secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
        if not isinstance(signature, str) or not hmac.compare_digest(expected, signature):
            raise PaymentError("Invalid checkout signature")

    def webhook(self, body, signature):
        if not isinstance(body, bytes) or len(body) > 262144:
            raise PaymentError("Invalid webhook size")
        expected = hmac.new(self._webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        if not isinstance(signature, str) or not hmac.compare_digest(expected, signature):
            raise PaymentError("Invalid webhook signature")
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise PaymentError("Invalid webhook")
        return payload


class Payments:
    def __init__(self, store, gateway, catalogue, *, clock=time.time):
        self.store, self.gateway, self.catalogue, self.clock = store, gateway, catalogue, clock

    def _key(self, key):
        return self.gateway.mode + ":" + key

    def checkout(self, owner, product, request_id):
        if product not in self.catalogue or not request_id or len(request_id) > 128:
            raise PaymentError("Unknown product or invalid request ID")
        item = self.catalogue[product]
        amount, currency = item["amount"], item["currency"]
        if type(amount) is not int or amount <= 0 or not re.fullmatch(r"[A-Z]{3}", currency):
            raise PaymentError("Invalid catalogue")
        key = self._key(hashlib.sha256(json.dumps([owner, request_id]).encode()).hexdigest())
        with self.store.transaction():
            existing = self.store.get("orders", key)
            if existing:
                if existing["product"] != product:
                    raise PaymentError("Request ID reused for another product")
                if existing["state"] == "creating":
                    raise PaymentError("Creation outcome unknown; reconcile before retry")
                return self._checkout_view(existing)
            row = {"key": key, "owner": owner, "product": product, "amount": amount, "currency": currency, "state": "creating", "created": self.clock()}
            self.store.put("orders", key, row)
        # An uncertain external create is deliberately never automatically retried.
        order = self.gateway.create_order(amount, currency, key[-40:])
        if order.get("amount") != amount or order.get("currency") != currency or not isinstance(order.get("id"), str):
            raise PaymentError("Provider order mismatch; review required")
        with self.store.transaction():
            row.update(order_id=order["id"], state="pending")
            self.store.put("orders", key, row)
            self.store.put("order_ids", self._key(order["id"]), {"key": key})
        return self._checkout_view(row)

    def _checkout_view(self, row):
        return {"key": self.gateway.key_id, "order_id": row["order_id"], "amount": row["amount"], "currency": row["currency"], "state": row["state"]}

    def confirm(self, owner, order_id, payment_id, signature):
        self.gateway.verify_checkout(order_id, payment_id, signature)
        link = self.store.get("order_ids", self._key(order_id))
        row = self.store.get("orders", link["key"]) if link else None
        if not row or row["owner"] != owner:
            raise PaymentError("Order not found")
        payment = self.gateway.payment(payment_id)
        return self._capture(row, payment)

    def _capture(self, row, payment):
        if payment.get("order_id") != row["order_id"] or payment.get("amount") != row["amount"] or payment.get("currency") != row["currency"] or payment.get("status") != "captured" or payment.get("amount_refunded", 0) != 0 or not payment.get("id"):
            raise PaymentError("Captured payment does not match order")
        with self.store.transaction():
            current = self.store.get("orders", row["key"])
            if current["state"] == "refunded" or self.store.get("payment_revocations", self._key(payment["id"])):
                raise PaymentError("Refunded order")
            if current.get("payment_id") and current["payment_id"] != payment["id"]:
                raise PaymentError("Order already bound")
            current.update(state="paid", payment_id=payment["id"])
            self.store.put("orders", row["key"], current)
            # Durable receipt can be polled/processed idempotently by business code.
            receipt = {"id": self._key(payment["id"]), "owner": row["owner"], "product": row["product"], "amount": row["amount"], "currency": row["currency"], "state": "paid"}
            self.store.put("receipts", receipt["id"], receipt)
        return receipt

    def receive_webhook(self, body, signature):
        event = self.gateway.webhook(body, signature)
        key = self._key(hashlib.sha256(body).hexdigest())
        if self.store.get("payment_events", key):
            return {"duplicate": True}
        kind = event.get("event")
        if kind not in {"payment.captured", "refund.processed"}:
            return {"ignored": True}
        entity = event.get("payload", {}).get("payment", {}).get("entity", {})
        if kind == "payment.captured":
            link = self.store.get("order_ids", self._key(entity.get("order_id", "")))
            if not link:
                return {"ignored": True}
            row = self.store.get("orders", link["key"])
            self._capture(row, entity)
        else:
            refund = event.get("payload", {}).get("refund", {}).get("entity", {})
            pid = refund.get("payment_id")
            if not isinstance(pid, str) or not pid:
                raise PaymentError("Invalid refund payment")
            self.store.put("payment_revocations", self._key(pid), {"payment_id": pid, "received": self.clock()})
            receipt = self.store.get("receipts", self._key(pid or ""))
            if not receipt:
                return {"ignored": True}
            # Conservatively revoke the entire receipt even for a partial refund.
            with self.store.transaction():
                receipt["state"] = "refunded"
                self.store.put("receipts", receipt["id"], receipt)
                for row in self.store.all("orders"):
                    if row.get("payment_id") == pid and row["key"].startswith(self.gateway.mode + ":"):
                        row["state"] = "refunded"
                        self.store.put("orders", row["key"], row)
        self.store.put("payment_events", key, {"kind": kind, "received": self.clock()})
        return {"accepted": True}

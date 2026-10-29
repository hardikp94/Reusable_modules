# Razorpay payments

Install `[razorpay]` and initialize an official Razorpay SDK client explicitly. Provider SDK/client configuration must set finite timeouts and avoid automatic retries of creation calls. Keep credentials server-side.

```python
import os
import razorpay
from reusable_foundations.payments import Razorpay, Payments
from reusable_foundations.fastapi import payment_router

sdk = razorpay.Client(auth=(os.environ["RAZORPAY_KEY_ID"], os.environ["RAZORPAY_KEY_SECRET"]))
gateway = Razorpay(sdk, key_id=os.environ["RAZORPAY_KEY_ID"],
    key_secret=os.environ["RAZORPAY_KEY_SECRET"],
    webhook_secret=os.environ["RAZORPAY_WEBHOOK_SECRET"], mode="test")
payments = Payments(store, gateway, {"course": {"amount": 9900, "currency": "INR"}})
app.include_router(payment_router(payments, identity, limiter, origin=app_origin))
```

The client supplies a product identifier and stable request ID, not an amount. The server owns prices and binds each created order to an authenticated account. Each repeat of `(mode,owner,request_id)` returns the same order. If creation times out or its local persistence fails, the intent remains `creating` and blocks automatic recreation: reconcile using the saved provider receipt reference before manual repair.

```javascript
import {checkout} from "@reusable-foundations/react/checkout";
const requestId = crypto.randomUUID(); // retain for this purchase and every retry
const receipt = await checkout({client, product: "course", requestId, name: "My application"});
```

Checkout dynamically loads the official browser script unless you inject `RazorpayClass`. The server verifies HMAC using its stored order ID, fetches the payment and checks captured status, amount, currency, order linkage and refund amount. Browser success alone cannot grant access. On dismissal/error, refresh/reconcile rather than assuming the payment failed irreversibly.

## Webhooks and fulfillment

Configure the NEW project's gateway webhook URL as `/billing/webhook`. Pass exact raw bytes and `X-Razorpay-Signature`. The adapter limits body size to 256 KiB, verifies HMAC using the separate webhook secret and deduplicates signed bodies. It handles `payment.captured` and `refund.processed`; other events are ignored. Refunds create a durable payment revocation even when they arrive before capture. Any partial refund conservatively revokes the whole receipt. Refund initiation/disputes/chargebacks are not implemented.

`payments.confirm` and accepted capture webhooks write a durable `receipts` record. Business code should read the receipt by `mode:payment_id`, verify its owner/product/state, then grant benefits with that same stable receipt ID. Never grant from request JSON. Recheck payment revocation at access or process it through a durable reconciliation job; the toolkit cannot atomically transact with your external application.

A late capture after a recorded refund is rejected rather than reactivating access; operational reconciliation should resolve persistent provider retries. SDK errors propagate; the host should map them to a generic 502/503, log only sanitized internal diagnostics and keep uncertainty visible. Provider success followed by process failure is not an exactly-once guarantee.

Subscription events use the separate [Subscriptions](subscriptions.md) integration. No remote provider setup, real checkout, refund or delivery was tested. See the official [integration flow](https://razorpay.com/docs/payments/server-integration/python/integration-steps/) and [webhook validation](https://razorpay.com/docs/webhooks/validate-test/).

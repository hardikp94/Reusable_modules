# Subscriptions and entitlements

```python
from reusable_foundations.entitlements import Subscriptions

subscriptions = Subscriptions(store, gateway, {
    "monthly": {"provider_plan": "plan_YOUR_PROJECT", "total_count": 12,
        "amount": 9900, "currency": "INR", "features": ["course_library"]}
})
record = subscriptions.create(user_id, "monthly", request_id)
# Authorize the provider subscription through your host's recurring Checkout UI.
subscriptions.reconcile(user_id, record["id"])
subscriptions.record_paid_period(user_id, record["id"], provider_invoice_id)
allowed = subscriptions.allows(user_id, record["id"], "course_library")
subscriptions.cancel(user_id, record["id"])
```

The service binds subscription ID, mode, owner and configured plan. Creation uses durable intents and blocks unknown outcomes. `reconcile` fetches provider state and verifies the binding. Active state by itself never establishes paid access. `record_paid_period` fetches the invoice and linked payment server-side, checks paid/captured status, subscription linkage, exact configured amount/currency, no refunded amount and invoice billing boundaries. A payment cannot grant another subscription/period.

`allows` requires a currently valid, unrevoked paid interval, allowed provider state and feature in the configured plan. Future intervals cannot unlock early. Restricted states deny immediately. Cancel renewal requests cycle-end cancellation; valid paid access can remain until expiry. `revoke_payment(owner, subscription_id, payment_id)` revokes that paid interval after trusted refund/dispute evidence. Replaying a revoked invoice cannot re-enable it.

The host must authenticate/authorize all calls, provide recurring subscription checkout UI, verify subscription/invoice/refund webhooks and schedule reconciliation. The supplied payment router's one-time checkout and webhook processing do not automatically run subscription reconciliation. This separation is intentional and must be wired in each project. Failure to ingest provider restrictions/refunds leaves local state stale. Use fresh reconciliation before sensitive access according to an explicit application policy.

The initial adapter supports fixed-price, one-unit periods matching the configured amount. Taxes, discounts, quantities, prorations, add-ons and multiple invoice payments need a reviewed price/period adapter. There is no automatic grace period. A real gateway compatibility test is still required for your account, SDK version and invoice shapes; offline tests use representative synthetic records. Keep feature definitions separate from product branding.

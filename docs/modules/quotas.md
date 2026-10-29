# Usage quotas, trials and credit packs

```python
import time
from reusable_foundations.entitlements import Quotas, AllowanceError

quotas = Quotas(store)
quotas.grant(user_id, "trial:" + user_id, 5,
    expires=int(time.time()) + 30 * 86400, kind="trial")

reservation = quotas.reserve(user_id, operation_id)
if reservation["state"] == "reserved":
    try:
        result = perform_application_operation()
    except Exception:
        quotas.settle(user_id, reservation["id"], success=False)
        raise
    quotas.settle(user_id, reservation["id"], success=True)
```

A grant ID is globally unique within the store. Use namespaced IDs such as `trial:user_id`, `paid:subscription_id:period_end` or `topup:mode:payment_id`. Repeating an identical grant is safe; trying to reuse its ID with changed owner/limit/expiry fails. Trials, paid allowances and purchased credits use the same ledger and differ by `kind` and your grant policy. The library does not decide when a user is trial eligible.

Reservation checks and increments happen in one serialized transaction. Earliest-expiring eligible grant is selected; `kind=` can restrict consumption. One reservation must fit a single grant; combining insufficient balances from several grants is not supported. `balance` sums eligible unreserved units. Use unique operation IDs per actual operation, retained across retries.

**Usage reservation is not operation execution deduplication.** A repeated reserve returns its existing `reserved`, `consumed` or `released` state. Two workers with the same operation ID can receive the same reserved record; the application must claim/deduplicate actual work and persist results separately. Never blindly rerun already consumed/released operations. `settle` is idempotent for the same outcome and rejects a contradictory outcome.

In-progress units remain reserved after process crashes. Implement reconciliation against your actual operation records; do not automatically release just because time passed if provider work may have happened. Expired/revoked grants cannot admit new reservations. Existing reservations can settle after expiry/revocation to preserve accounting.

To sell credits, verify a payment receipt first, then call `grant` with its stable receipt ID and configured units/expiry. On refund revoke the associated grant and enforce receipt state. Paid subscription access and quota availability are independent checks. Exhausted allowance must not create another recurring subscription automatically.

# Analytics foundation

```python
from reusable_foundations.observability import Analytics
analytics = Analytics(store, {"page_view": ["page"], "purchase_view": ["product"]}, retention=180*86400)
analytics.track("page_view", {"page": "/pricing"}, consent=True, event_id=event_id)
counts = analytics.counts()
analytics.purge()
```

Unknown events/properties fail. Consent=False stores nothing. Explicit event IDs deduplicate repeated submissions. Use random opaque IDs scoped to your collection policy, not email/phone. Redaction is the same conservative helper as Audit; it is not a complete personal-data detector. The host must validate property values and enforce its consent/retention rules.

`counts` ignores events older than retention; `purge` deletes those records. Schedule purge explicitly, since SQLite has no TTL job. Read/query authorization, inbound rate limits and dashboard UI belong to the host. Browser-submitted traffic is forgeable and must never establish payments, security events or entitlement.

This module provides basic event collection and counts, not funnels, attribution, anonymous session tracking or a BI platform. Its scanning storage adapter is intended for modest datasets; use indexed aggregation at scale.
